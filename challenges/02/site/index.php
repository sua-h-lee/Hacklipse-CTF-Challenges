<?php
declare(strict_types=1);

session_start([
    'use_strict_mode' => true,
    'cookie_httponly' => true,
    'cookie_samesite' => 'Lax',
    'cookie_secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
]);
header('Cache-Control: no-store');
$_SESSION['csrf'] ??= bin2hex(random_bytes(32));

$db = new PDO('sqlite:' . (getenv('APP_DB') ?: sys_get_temp_dir() . '/hkl-member02.sqlite3'));
$db->exec('PRAGMA busy_timeout = 5000');
$db->exec('CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
)');
if (!$db->query('SELECT 1 FROM members LIMIT 1')->fetchColumn()) {
    $db->beginTransaction();
    $insert = $db->prepare('INSERT INTO members VALUES (?, ?, ?) ON CONFLICT(id) DO NOTHING');
    foreach (require (getenv('APP_SEED') ?: __DIR__ . '/users.php') as $user) {
        $insert->execute($user);
    }
    $db->commit();
}

$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$page = $path === '/board' ? 'board' : ($_GET['page'] ?? 'login');
if (!in_array($page, ['login', 'register', 'board'], true)) {
    http_response_code(404);
    exit;
}
if ($page === 'board' && !isset($_SESSION['user'])) {
    header('Location: /?page=login', true, 303);
    exit;
}

$posts = [];
if ($page === 'board' && $_SERVER['REQUEST_METHOD'] === 'GET') {
    $boardId = array_key_exists('id', $_GET)
        ? filter_var($_GET['id'], FILTER_VALIDATE_INT, ['options' => ['min_range' => 1]])
        : (int) $_SESSION['user']['id'];
    $findOwner = $db->prepare('SELECT username FROM members WHERE id = ?');
    $findOwner->execute([$boardId]);
    $owner = $findOwner->fetchColumn();
    if ($boardId === false || $owner === false) {
        http_response_code(404);
        exit('게시판을 찾을 수 없습니다.');
    }
    $table = 'posts_' . $boardId;
    $db->exec("CREATE TABLE IF NOT EXISTS $table (post_id INTEGER PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL)");
    $seedPosts = require dirname(getenv('APP_SEED') ?: __DIR__ . '/users.php') . '/posts.php';
    $insert = $db->prepare("INSERT INTO $table VALUES (?, ?, ?) ON CONFLICT(post_id) DO NOTHING");
    foreach ($seedPosts[$boardId] ?? [] as $post) {
        $insert->execute($post);
    }
    $posts = $db->query("SELECT post_id, title, content FROM $table ORDER BY post_id")->fetchAll(PDO::FETCH_ASSOC);
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $token = $_POST['csrf'] ?? null;
    if (!is_string($token) || !hash_equals($_SESSION['csrf'], $token)) {
        http_response_code(403);
        exit;
    }
    if ($page === 'board') {
        $_SESSION = [];
        session_destroy();
        header('Location: /?page=login', true, 303);
        exit;
    }

    $username = $_POST['username'] ?? null;
    $password = $_POST['password'] ?? null;
    if (!is_string($username) || !preg_match('/\A[a-zA-Z0-9_]{1,64}\z/', $username)
        || !is_string($password) || $password === '' || strlen($password) > 72 || str_contains($password, "\0")) {
        $error = '아이디와 비밀번호를 확인해 주세요.';
    } elseif ($page === 'register') {
        $insert = $db->prepare('INSERT INTO members (username, password_hash)
            SELECT ?, ? WHERE NOT EXISTS (SELECT 1 FROM members WHERE username = ?)');
        $insert->execute([$username, password_hash($password, PASSWORD_DEFAULT), $username]);
        if ($insert->rowCount() === 1) {
            header('Location: /?page=login', true, 303);
            exit;
        }
        $error = '이미 사용 중인 아이디입니다.';
    } else {
        $find = $db->prepare('SELECT id, username, password_hash FROM members WHERE username = ?');
        $find->execute([$username]);
        $user = $find->fetch(PDO::FETCH_ASSOC);
        if ($user && password_verify($password, $user['password_hash'])) {
            session_regenerate_id(true);
            $_SESSION['user'] = ['id' => $user['id'], 'username' => $user['username']];
            header('Location: /board?id=' . (int) $user['id'], true, 303);
            exit;
        }
        $error = '아이디 또는 비밀번호가 올바르지 않습니다.';
    }
}

function escape(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

$heading = ['login' => '로그인', 'register' => '회원가입', 'board' => '게시판'][$page];
?>
<!doctype html>
<html lang="ko">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= $heading ?></title>
<style>
body { max-width: 36rem; margin: 3rem auto; padding: 0 1rem; font: 1rem system-ui, sans-serif; }
label { display: block; margin-bottom: 1rem; }
input:not([type=hidden]) { display: block; width: 100%; box-sizing: border-box; padding: .5rem; }
</style>
<main>
  <h1><?= $heading ?></h1>
  <?php if ($error !== ''): ?><p role="alert"><?= escape($error) ?></p><?php endif; ?>
  <form method="post">
    <input type="hidden" name="csrf" value="<?= escape($_SESSION['csrf']) ?>">
    <?php if ($page === 'board'): ?>
      <p><?= escape($_SESSION['user']['username']) ?> · ID <?= (int) $_SESSION['user']['id'] ?></p>
      <button>로그아웃</button>
    <?php else: ?>
      <label>아이디<input name="username" autocomplete="username" maxlength="64" required></label>
      <label>비밀번호<input type="password" name="password" autocomplete="<?= $page === 'register' ? 'new-password' : 'current-password' ?>" required></label>
      <button><?= $heading ?></button>
    <?php endif; ?>
  </form>
  <?php if ($page === 'board'): ?>
    <h2><?= escape($owner) ?>의 게시판</h2>
    <?php if ($posts === []): ?><p>게시글이 없습니다.</p><?php endif; ?>
    <?php foreach ($posts as $post): ?>
      <article>
        <h3><?= escape($post['title']) ?></h3>
        <small>#<?= (int) $post['post_id'] ?> · <?= escape($owner) ?></small>
        <p><?= escape($post['content']) ?></p>
      </article>
    <?php endforeach; ?>
  <?php else: ?>
    <p><a href="/?page=<?= $page === 'login' ? 'register' : 'login' ?>"><?= $page === 'login' ? '회원가입' : '로그인' ?></a></p>
  <?php endif; ?>
</main>
</html>
