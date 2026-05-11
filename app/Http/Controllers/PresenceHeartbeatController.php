<?php

namespace App\Http\Controllers;

use App\Events\MemberOnline;
use App\Support\DeviceToken;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class PresenceHeartbeatController extends Controller
{
    public function __invoke(Request $request): JsonResponse
    {
        $device = DeviceToken::fromRequest($request);

        if (! $device) {
            abort(Response::HTTP_UNAUTHORIZED);
        }

        $wasOffline = $device->offline_at !== null || $device->online_at === null;

        $device->forceFill([
            'last_seen_at' => now(),
            'online_at' => $device->online_at ?? now(),
            'offline_at' => null,
        ])->save();

        $device->refresh()->load(['team', 'user']);

        if ($wasOffline) {
            MemberOnline::dispatch($device);
        }

        return response()->json([
            'status' => 'online',
            'last_seen_at' => $device->last_seen_at?->toISOString(),
            'team' => [
                'id' => $device->team->id,
                'name' => $device->team->name,
            ],
            'user' => [
                'id' => $device->user->id,
                'name' => $device->user->name,
                'avatar_url' => $device->user->avatar_url,
            ],
            'device' => [
                'id' => $device->id,
                'device_uuid' => $device->device_uuid,
                'name' => $device->name,
                'platform' => $device->platform,
                'hostname' => $device->hostname,
            ],
        ]);
    }
}
