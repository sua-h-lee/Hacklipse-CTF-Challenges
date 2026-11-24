<?php
declare(strict_types=1);

$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if (!in_array($path, ['/', '/info', '/report'], true)) {
    http_response_code(404);
    exit;
}

require __DIR__ . '/index.php';
