<?php

namespace App\Http\Controllers;

use App\Support\DeviceToken;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class BroadcastAuthController extends Controller
{
    public function __invoke(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'socket_id' => ['required', 'string'],
            'channel_name' => ['required', 'string'],
        ]);

        $device = DeviceToken::fromRequest($request);
        $channelName = $validated['channel_name'];

        if (! $device || ! preg_match('/^private-team\.(\d+)$/', $channelName, $matches)) {
            abort(Response::HTTP_FORBIDDEN);
        }

        if ((int) $matches[1] !== $device->team_id) {
            abort(Response::HTTP_FORBIDDEN);
        }

        $signature = hash_hmac(
            'sha256',
            $validated['socket_id'].':'.$channelName,
            (string) config('broadcasting.connections.reverb.secret'),
        );

        return response()->json([
            'auth' => config('broadcasting.connections.reverb.key').':'.$signature,
        ]);
    }
}
