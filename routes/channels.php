<?php

use App\Support\DeviceToken;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Broadcast;

Broadcast::channel('App.Models.User.{id}', function ($user, $id) {
    return (int) $user->id === (int) $id;
});

Broadcast::channel('team.{teamId}', function (Request $request, int $teamId) {
    $device = DeviceToken::fromRequest($request);

    return $device && $device->team_id === $teamId;
});
