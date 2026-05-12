<?php

use App\Http\Controllers\BroadcastAuthController;
use App\Http\Controllers\CreateRoomController;
use App\Http\Controllers\JoinController;
use App\Http\Controllers\PresenceHeartbeatController;
use App\Http\Controllers\PresenceProfileController;
use Illuminate\Support\Facades\Route;

Route::post('/broadcasting/auth', BroadcastAuthController::class);
Route::post('/join', JoinController::class);
Route::post('/presence/heartbeat', PresenceHeartbeatController::class);
Route::post('/presence/profile', PresenceProfileController::class);
Route::post('/rooms', CreateRoomController::class);
