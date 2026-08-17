<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Schema;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        // Настройка длины строк по умолчанию для старых версий MySQL (MySQL 5.7.44 на хостинге REG.RU)
        // Предотвращает ошибку: "1071 Specified key was too long; max key length is 767 bytes"
        Schema::defaultStringLength(191);
    }
}
