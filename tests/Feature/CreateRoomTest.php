<?php

namespace Tests\Feature;

use App\Models\Device;
use App\Models\InviteCode;
use App\Models\Team;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class CreateRoomTest extends TestCase
{
    use RefreshDatabase;

    public function test_user_can_create_room_by_invite_code(): void
    {
        $response = $this->postJson('/api/rooms', [
            'name' => 'Данил',
            'invite_code' => 'ROOM-123',
            'device_uuid' => '550e8400-e29b-41d4-a716-446655440000',
            'device_name' => 'Linux laptop',
            'platform' => 'linux',
            'hostname' => 'local',
        ]);

        $response
            ->assertCreated()
            ->assertJsonPath('team.name', 'Комната ROOM-123')
            ->assertJsonPath('user.name', 'Данил')
            ->assertJsonPath('device.device_uuid', '550e8400-e29b-41d4-a716-446655440000')
            ->assertJsonStructure([
                'device_token',
                'team' => ['id', 'name'],
                'user' => ['id', 'name', 'avatar_url'],
                'device' => ['id', 'device_uuid', 'name', 'platform', 'hostname'],
            ]);

        $this->assertDatabaseHas('invite_codes', [
            'code' => 'ROOM-123',
        ]);
    }

    public function test_room_invite_code_must_be_unique(): void
    {
        $team = Team::query()->create(['name' => 'Existing']);

        InviteCode::query()->create([
            'team_id' => $team->id,
            'code' => 'ROOM-123',
        ]);

        $this
            ->postJson('/api/rooms', [
                'name' => 'Данил',
                'invite_code' => 'ROOM-123',
            ])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('invite_code');
    }

    public function test_existing_device_can_create_another_room(): void
    {
        $team = Team::query()->create(['name' => 'Old Room']);
        $user = User::query()->create([
            'team_id' => $team->id,
            'name' => 'Данил',
            'email' => 'old-device@example.test',
            'password' => 'password',
        ]);

        Device::query()->create([
            'team_id' => $team->id,
            'user_id' => $user->id,
            'device_uuid' => '550e8400-e29b-41d4-a716-446655440000',
            'name' => 'Linux laptop',
            'platform' => 'linux',
            'hostname' => 'local',
            'token_hash' => hash('sha256', 'old-token'),
            'last_seen_at' => now(),
            'online_at' => now(),
        ]);

        $response = $this->postJson('/api/rooms', [
            'name' => 'Данил',
            'invite_code' => 'ROOM-456',
            'device_uuid' => '550e8400-e29b-41d4-a716-446655440000',
            'device_name' => 'Linux laptop',
            'platform' => 'linux',
            'hostname' => 'local',
        ]);

        $response
            ->assertCreated()
            ->assertJsonPath('team.name', 'Комната ROOM-456')
            ->assertJsonPath('device.device_uuid', '550e8400-e29b-41d4-a716-446655440000');

        $this->assertDatabaseCount('devices', 1);
        $this->assertDatabaseHas('devices', [
            'device_uuid' => '550e8400-e29b-41d4-a716-446655440000',
            'token_hash' => hash('sha256', $response->json('device_token')),
        ]);
    }
}
