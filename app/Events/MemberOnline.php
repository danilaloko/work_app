<?php

namespace App\Events;

use App\Models\Device;
use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcastNow;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class MemberOnline implements ShouldBroadcastNow
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    public function __construct(public Device $device) {}

    public function broadcastAs(): string
    {
        return 'member_online';
    }

    /**
     * @return array<int, PrivateChannel>
     */
    public function broadcastOn(): array
    {
        return [
            new PrivateChannel('team.'.$this->device->team_id),
        ];
    }

    /**
     * @return array<string, mixed>
     */
    public function broadcastWith(): array
    {
        return [
            'team_id' => $this->device->team_id,
            'user' => [
                'id' => $this->device->user->id,
                'name' => $this->device->user->name,
                'avatar_url' => $this->device->user->avatar_url,
                'avatar_key' => $this->device->user->avatar_key,
                'item_key' => $this->device->user->item_key,
            ],
            'device' => [
                'id' => $this->device->id,
                'device_uuid' => $this->device->device_uuid,
                'name' => $this->device->name,
                'platform' => $this->device->platform,
                'hostname' => $this->device->hostname,
                'last_seen_at' => $this->device->last_seen_at?->toISOString(),
                'online_at' => $this->device->online_at?->toISOString(),
            ],
        ];
    }
}
