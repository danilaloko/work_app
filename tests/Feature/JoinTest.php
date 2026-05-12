<?php

namespace Tests\Feature;

use App\Models\InviteCode;
use App\Models\Team;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class JoinTest extends TestCase
{
    use RefreshDatabase;

    public function test_device_can_join_team_by_invite_code(): void
    {
        $team = Team::query()->create(['name' => 'Demo Team']);

        InviteCode::query()->create([
            'team_id' => $team->id,
            'code' => 'DEMO-TEAM',
        ]);

        $response = $this->postJson('/api/join', [
            'name' => 'Dan',
            'invite_code' => 'DEMO-TEAM',
            'device_uuid' => '550e8400-e29b-41d4-a716-446655440000',
            'device_name' => 'Work laptop',
            'platform' => 'linux',
            'hostname' => 'dan-laptop',
            'avatar_key' => 'robot',
            'item_key' => 'laptop',
        ]);

        $response
            ->assertCreated()
            ->assertJsonPath('team.name', 'Demo Team')
            ->assertJsonPath('user.name', 'Dan')
            ->assertJsonPath('user.avatar_key', 'robot')
            ->assertJsonPath('user.item_key', 'laptop')
            ->assertJsonPath('device.device_uuid', '550e8400-e29b-41d4-a716-446655440000')
            ->assertJsonStructure([
                'device_token',
                'team' => ['id', 'name'],
                'user' => ['id', 'name', 'avatar_url', 'avatar_key', 'item_key'],
                'device' => ['id', 'device_uuid', 'name', 'platform', 'hostname'],
            ]);

        $this->assertDatabaseHas('devices', [
            'team_id' => $team->id,
            'device_uuid' => '550e8400-e29b-41d4-a716-446655440000',
            'token_hash' => hash('sha256', $response->json('device_token')),
        ]);
    }

    public function test_join_requires_valid_invite_code(): void
    {
        $response = $this->postJson('/api/join', [
            'name' => 'Dan',
            'invite_code' => 'WRONG-CODE',
        ]);

        $response
            ->assertUnprocessable()
            ->assertJsonValidationErrors('invite_code');
    }
}
