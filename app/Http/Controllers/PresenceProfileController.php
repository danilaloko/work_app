<?php

namespace App\Http\Controllers;

use App\Support\DeviceToken;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Symfony\Component\HttpFoundation\Response;

class PresenceProfileController extends Controller
{
    public function __invoke(Request $request): JsonResponse
    {
        $device = DeviceToken::fromRequest($request);

        if (! $device) {
            abort(Response::HTTP_UNAUTHORIZED);
        }

        $validated = $request->validate([
            'avatar_key' => ['required', 'string', Rule::in(['cat', 'dog', 'fox', 'robot'])],
            'item_key' => ['required', 'string', Rule::in(['coffee', 'laptop', 'book', 'plant'])],
        ]);

        $device->user->forceFill($validated)->save();
        $device->refresh()->load(['team', 'user']);

        return response()->json([
            'team' => [
                'id' => $device->team->id,
                'name' => $device->team->name,
            ],
            'user' => [
                'id' => $device->user->id,
                'name' => $device->user->name,
                'avatar_url' => $device->user->avatar_url,
                'avatar_key' => $device->user->avatar_key,
                'item_key' => $device->user->item_key,
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
