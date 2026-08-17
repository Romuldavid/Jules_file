<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class HomeController extends Controller
{
    /**
     * Отображение главной страницы сайта mufta40.ru
     */
    public function index()
    {
        $message = "Сайт mufta40.ru успешно работает на Laravel 11!";

        return view('welcome', compact('message'));
    }
}
