<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\HomeController;

/*
|--------------------------------------------------------------------------
| Web Routes
|--------------------------------------------------------------------------
|
| Здесь регистрируются маршруты веб-приложения для mufta40.ru
|
*/

Route::get('/', [HomeController::class, 'index'])->name('home');
