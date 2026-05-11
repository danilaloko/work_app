<?php

namespace App\Http\Controllers;

use App\Events\MemberOnline;
use App\Models\Device;
use App\Models\InviteCode;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;

class JoinController extends Controller
{
    /**
     * Register a desktop device by team invite code.
     */
    public function __invoke(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => ['required', 'string', 'max:120'],
            'invite_code' => ['required', 'string', 'max:64'],
            'device_uuid' => ['nullable', 'uuid'],
            'device_name' => ['nullable', 'string', 'max:120'],
            'platform' => ['nullable', 'string', 'max:80'],
            'hostname' => ['nullable', 'string', 'max:120'],
            'avatar_url' => ['nullable', 'url', 'max:2048'],
        ]);

        $inviteCode = InviteCode::query()
            ->with('team')
            ->where('code', $validated['invite_code'])
            ->first();

        if (! $inviteCode || $inviteCode->used_at || $inviteCode->expires_at?->isPast()) {
            throw ValidationException::withMessages([
                'invite_code' => 'Invite code is invalid or expired.',
            ]);
        }

        $plainToken = Str::random(64);
        $deviceUuid = $validated['device_uuid'] ?? (string) Str::uuid();

        [$user, $device] = DB::transaction(function () use ($validated, $inviteCode, $plainToken, $deviceUuid): array {
            $user = User::query()->create([
                'team_id' => $inviteCode->team_id,
                'name' => $validated['name'],
                'email' => Str::uuid().'@presence.local',
                'password' => Str::password(32),
                'avatar_url' => $validated['avatar_url'] ?? null,
            ]);

            $device = Device::query()->updateOrCreate(
                ['device_uuid' => $deviceUuid],
                [
                    'team_id' => $inviteCode->team_id,
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

            return [$user, $device];
        });

        $device->load(['team', 'user']);
        MemberOnline::dispatch($device);

        return response()->json([
            'device_token' => $plainToken,
            'team' => [
                'id' => $inviteCode->team->id,
                'name' => $inviteCode->team->name,
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
