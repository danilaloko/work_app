<?php

namespace Database\Seeders;

use App\Models\InviteCode;
use App\Models\Team;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    use WithoutModelEvents;

    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        $team = Team::query()->firstOrCreate([
            'name' => 'Demo Team',
        ]);

        InviteCode::query()->firstOrCreate([
            'code' => 'DEMO-TEAM',
        ], [
            'team_id' => $team->id,
        ]);
    }
}
