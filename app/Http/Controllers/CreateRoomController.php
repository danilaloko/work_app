<?php

namespace App\Http\Controllers;

use App\Events\MemberOnline;
use App\Models\Device;
use App\Models\InviteCode;
use App\Models\Team;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class CreateRoomController extends Controller
{
    /**
     * Create a room and register the first desktop device in it.
     */
    public function __invoke(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => ['required', 'string', 'max:120'],
            'invite_code' => ['required', 'string', 'max:64', 'unique:invite_codes,code'],
            'device_uuid' => ['nullable', 'uuid'],
            'device_name' => ['nullable', 'string', 'max:120'],
            'platform' => ['nullable', 'string', 'max:80'],
            'hostname' => ['nullable', 'string', 'max:120'],
            'avatar_url' => ['nullable', 'url', 'max:2048'],
        ]);

        $plainToken = Str::random(64);
        $deviceUuid = $validated['device_uuid'] ?? (string) Str::uuid();

        [$team, $user, $device] = DB::transaction(function () use ($validated, $plainToken, $deviceUuid): array {
            $team = Team::query()->create([
                'name' => 'Комната '.$validated['invite_code'],
            ]);

            InviteCode::query()->create([
                'team_id' => $team->id,
                'code' => $validated['invite_code'],
            ]);

            $user = User::query()->create([
                'team_id' => $team->id,
                'name' => $validated['name'],
                'email' => Str::uuid().'@presence.local',
                'password' => Str::password(32),
                'avatar_url' => $validated['avatar_url'] ?? null,
            ]);

            $device = Device::query()->updateOrCreate(
                ['device_uuid' => $deviceUuid],
                [
                    'team_id' => $team->id,
                    'user_id' => $user->id,
                    'name' => $validated['device_name'] ?? null,
                    'platform' => $validated['platform'] ?? null,
                    'hostname' => $validated['hostname'] ?? null,
                    'token_hash' => hash('sha256', $plainToken),
                    'last_seen_at' => now(),
                    'online_at' => now(),
                    'offline_at' => null,
                ],
            );

            return [$team, $user, $device];
        });

        $device->load(['team', 'user']);
        MemberOnline::dispatch($device);

        return response()->json([
            'device_token' => $plainToken,
            'team' => [
                'id' => $team->id,
                'name' => $team->name,
            ],
            'user' => [
                'id' => $user->id,
                'name' => $user->name,
                'avatar_url' => $user->avatar_url,
            ],
            'device' => [
                'id' => $device->id,
                'device_uuid' => $device->device_uuid,
                'name' => $device->name,
                'platform' => $device->platform,
                'hostname' => $device->hostname,
            ],
        ], 201);
    }
}
