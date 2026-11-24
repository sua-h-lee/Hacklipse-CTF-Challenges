<?php
declare(strict_types=1);

$request = json_decode(stream_get_contents(STDIN), true, flags: JSON_THROW_ON_ERROR);
$headers = "Content-Type: application/x-www-form-urlencoded\r\n";
if (preg_match('/^[a-zA-Z0-9,-]{1,128}$/D', $request['cookie'])) {
    $headers .= "Cookie: PHPSESSID=" . $request['cookie'] . "\r\n";
}
$context = stream_context_create(['http' => [
    'method' => $request['method'],
    'header' => $headers,
    'content' => base64_decode($request['body'], true),
    'ignore_errors' => true,
    'follow_location' => 0,
    'timeout' => 2,
]]);
$body = file_get_contents('http://127.0.0.1:8080' . $request['path'], false, $context, 0, 262144);
if ($body === false) {
    exit(1);
}
$cookies = [];
foreach ($http_response_header as $header) {
    if (stripos($header, 'Set-Cookie: ') === 0) {
        $cookies[] = substr($header, 12);
    }
}
echo json_encode(['status' => (int) explode(' ', $http_response_header[0])[1],
    'cookies' => $cookies, 'body' => base64_encode($body)], JSON_THROW_ON_ERROR);
