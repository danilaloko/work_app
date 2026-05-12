<?php

namespace Tests\Feature;

use App\Events\MemberOffline;
use App\Events\MemberOnline;
use App\Models\Device;
use App\Models\Team;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Event;
use Tests\TestCase;

class PresenceTest extends TestCase
{
    use RefreshDatabase;

    public function test_broadcast_auth_accepts_device_token_for_own_team_channel(): void
    {
        [$team, $device, $token] = $this->createDevice();
        $socketId = '1234.5678';
        $channelName = 'private-team.'.$team->id;

        $response = $this
            ->withToken($token)
            ->postJson('/api/broadcasting/auth', [
                'socket_id' => $socketId,
                'channel_name' => $channelName,
            ]);

        $signature = hash_hmac(
            'sha256',
            $socketId.':'.$channelName,
            (string) config('broadcasting.connections.reverb.secret'),
        );

        $response
            ->assertOk()
            ->assertJsonPath('auth', config('broadcasting.connections.reverb.key').':'.$signature);

        $this->assertSame($team->id, $device->team_id);
    }

    public function test_broadcast_auth_rejects_other_team_channel(): void
    {
        [, , $token] = $this->createDevice();
        $otherTeam = Team::query()->create(['name' => 'Other Team']);

        $this
            ->withToken($token)
            ->postJson('/api/broadcasting/auth', [
                'socket_id' => '1234.5678',
                'channel_name' => 'private-team.'.$otherTeam->id,
            ])
            ->assertForbidden();
    }

    public function test_heartbeat_marks_offline_device_online(): void
    {
        Event::fake([MemberOnline::class]);

        [, $device, $token] = $this->createDevice([
            'online_at' => now()->subMinutes(10),
            'offline_at' => now()->subMinutes(5),
            'last_seen_at' => now()->subMinutes(10),
        ]);

        $response = $this
            ->withToken($token)
            ->postJson('/api/presence/heartbeat');

        $response
            ->assertOk()
            ->assertJsonPath('status', 'online')
            ->assertJsonPath('device.id', $device->id);

        $device->refresh();

        $this->assertNull($device->offline_at);
        $this->assertNotNull($device->last_seen_at);

        Event::assertDispatched(MemberOnline::class);
    }

    public function test_profile_update_stores_avatar_and_item_keys(): void
    {
        [, $device, $token] = $this->createDevice();

        $response = $this
            ->withToken($token)
            ->postJson('/api/presence/profile', [
                'avatar_key' => 'dog',
                'item_key' => 'plant',
            ]);

        $response
            ->assertOk()
            ->assertJsonPath('user.avatar_key', 'dog')
            ->assertJsonPath('user.item_key', 'plant')
            ->assertJsonPath('device.id', $device->id);

        $this->assertDatabaseHas('users', [
            'id' => $device->user_id,
            'avatar_key' => 'dog',
            'item_key' => 'plant',
        ]);
    }

    public function test_mark_offline_command_marks_stale_devices_offline(): void
    {
        Event::fake([MemberOffline::class]);

        [, $device] = $this->createDevice([
            'online_at' => now()->subMinutes(10),
            'offline_at' => null,
            'last_seen_at' => now()->subMinutes(10),
        ]);

        $this
            ->artisan('presence:mark-offline', ['--timeout' => 60])
            ->expectsOutput('Marked 1 device(s) offline.')
            ->assertSuccessful();

        $this->assertNotNull($device->refresh()->offline_at);

        Event::assertDispatched(MemberOffline::class);
    }

    /**
     * @param  array<string, mixed>  $deviceOverrides
     * @return array{0: Team, 1: Device, 2: string}
     */
    private function createDevice(array $deviceOverrides = []): array
    {
        $team = Team::query()->create(['name' => 'Demo Team']);
        $user = User::query()->create([
            'team_id' => $team->id,
            'name' => 'Dan',
            'email' => fake()->unique()->safeEmail(),
            'password' => 'password',
        ]);
        $token = 'test-device-token';

        $device = Device::query()->create(array_merge([
            'team_id' => $team->id,
            'user_id' => $user->id,
            'device_uuid' => fake()->uuid(),
            'name' => 'Work laptop',
            'platform' => 'linux',
            'hostname' => 'dan-laptop',
            'token_hash' => hash('sha256', $token),
            'online_at' => now(),
            'offline_at' => null,
            'last_seen_at' => now(),
        ], $deviceOverrides));

        return [$team, $device, $token];
    }
}
