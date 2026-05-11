<?php

namespace App\Support;

use App\Models\Device;
use Illuminate\Http\Request;

class DeviceToken
{
    public static function fromRequest(Request $request): ?Device
    {
        $token = $request->bearerToken();

        if (! $token) {
            return null;
        }

        return Device::query()
            ->with(['team', 'user'])
            ->where('token_hash', hash('sha256', $token))
            ->first();
    }
}
