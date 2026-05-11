<?php

namespace App\Console\Commands;

use App\Events\MemberOffline;
use App\Models\Device;
use Illuminate\Console\Command;

class MarkOfflineDevices extends Command
{
    protected $signature = 'presence:mark-offline {--timeout=60 : Seconds without heartbeat before a device is offline}';

    protected $description = 'Mark devices offline when heartbeat is stale.';

    public function handle(): int
    {
        $timeout = max(1, (int) $this->option('timeout'));
        $cutoff = now()->subSeconds($timeout);
        $count = 0;

        Device::query()
            ->with(['team', 'user'])
            ->whereNull('offline_at')
            ->whereNotNull('online_at')
            ->where('last_seen_at', '<', $cutoff)
            ->each(function (Device $device) use (&$count): void {
                $device->forceFill([
                    'offline_at' => now(),
                ])->save();

                $device->refresh()->load(['team', 'user']);
                MemberOffline::dispatch($device);

                $count++;
            });

        $this->info("Marked {$count} device(s) offline.");

        return self::SUCCESS;
    }
}
