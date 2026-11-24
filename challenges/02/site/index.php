<?php
declare(strict_types=1);
session_start();

$databasePath = getenv('APP_DB') ?: __DIR__ . '/data/users.sqlite3';
$directory = dirname($databasePath);
if (!is_dir($directory)) {
    mkdir($directory, 0700, true);
}
$database = new PDO('sqlite:' . $databasePath, options: [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$database->exec('PRAGMA busy_timeout = 5000');

$database->exec('CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
)');
$seed = getenv('INITIAL_USERS');
if ($seed !== false && $seed !== '') {
    $initialUsers = json_decode($seed, true, flags: JSON_THROW_ON_ERROR);
    $insert = $database->prepare('INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (?, ?, ?)');
    foreach ($initialUsers as $initialUser) {
        $insert->execute([$initialUser['id'], $initialUser['username'], password_hash($initialUser['password'], PASSWORD_DEFAULT)]);
    }
}

$initialPosts = [
    ['post_id' => 1, 'author' => 'h4nn4h', 'title' => '아니', 'content' => '게시글 신고 어디서 함? 누가 관리자야? 누구한테 신고해야함?'],
    ['post_id' => 2, 'author' => 'eatyummyfun', 'title' => '관리자님께', 'content' => 'young_wave 정지 부탁드립니다'],
    ['post_id' => 3, 'author' => 'lusterwind', 'title' => '정보', 'content' => '관리자한테 말할 거 있으면 /report 페이지로 가서 말하셈 거기로 가면 잘 봐주더라'],
    ['post_id' => 4, 'author' => 'eno', 'title' => '게시물로 말하면', 'content' => '게시물로 쓰시면 제가 못 봐여'],
    ['post_id' => 5, 'author' => 'young_wave', 'title' => '클라이밍 잘 하는 법', 'content' => '클라이밍을 잘 하려면 말이야'],
];

$profiles = [
    1 => ['user_name' => 'h4nn4h', 'email' => 'a@hacklipse.com', 'bio' => 'web'],
    2 => ['user_name' => 'eno', 'email' => 'enolee@hacklipse.com', 'bio' => 'system legend'],
    3 => ['user_name' => 'young_wave', 'email' => 'lib@hacklipse.com', 'bio' => 'recently into forensic'],
    4 => ['user_name' => 'lusterwind', 'email' => 'coffee@hacklipse.com', 'bio' => 'web'],
    5 => ['user_name' => 'eatyummyfun', 'email' => 'kang@hacklipse.com', 'bio' => 'V8 legend'],
];

$database->exec('CREATE TABLE IF NOT EXISTS posts (
    post_id INTEGER PRIMARY KEY,
    author TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL
)');
$seedPost = $database->prepare('INSERT OR IGNORE INTO posts (post_id, author, title, content) VALUES (?, ?, ?, ?)');
foreach ($initialPosts as $post) {
    $seedPost->execute([$post['post_id'], $post['author'], $post['title'], $post['content']]);
}

$error = '';
$message = '';
$profile = null;
$reportMessage = '';
$reportSummary = null;
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if ($path === '/info') {
    if (!isset($_SESSION['user_id'])) {
        http_response_code(401);
        $error = '프로필을 보려면 로그인해 주세요.';
    } else {
        $profileId = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT);
        if ($profileId === false || $profileId === null || !isset($profiles[$profileId])) {
            http_response_code(404);
            $error = '프로필을 찾을 수 없습니다.';
        } else {
            $profile = $profiles[$profileId];
        }
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';
    if ($action === 'submit_report') {
        if (!isset($_SESSION['user_id'])) {
            http_response_code(401);
            $error = '로그인이 필요합니다.';
        } else {
            $email = trim($_POST['admin_email'] ?? '');
            $reportedPostId = filter_var($_POST['post_id'] ?? '', FILTER_VALIDATE_INT);
            if (!filter_var($email, FILTER_VALIDATE_EMAIL) || $reportedPostId === false || $reportedPostId === null || $reportedPostId < 1) {
                $error = '관리자 이메일과 게시글 ID를 확인해 주세요.';
            } else {
                $reportSummary = ['email' => $email, 'post_id' => $reportedPostId];
                $reportMessage = '신고 내용을 접수했습니다.';
            }
        }
    } elseif ($action === 'create_post') {
        if (!isset($_SESSION['user_id'])) {
            http_response_code(401);
            $error = '로그인이 필요합니다.';
        } else {
            $title = trim($_POST['title'] ?? '');
            $content = $_POST['content'] ?? '';
            if ($title === '' || $content === '' || strlen($title) > 200 || strlen($content) > 10000) {
                $error = '제목과 내용을 확인해 주세요.';
            } else {
                do {
                    $postId = random_int(1000, 9999);
                    $exists = $database->prepare('SELECT 1 FROM posts WHERE post_id = ?');
                    $exists->execute([$postId]);
                } while ($exists->fetchColumn());
                $insertPost = $database->prepare('INSERT INTO posts (post_id, author, title, content) VALUES (?, ?, ?, ?)');
                $insertPost->execute([$postId, $_SESSION['username'], $title, $content]);
                $message = '게시글을 등록했습니다. 게시글 ID: ' . $postId;
            }
        }
    } else {
        $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    if (!in_array($action, ['register', 'login', 'logout'], true)) {
        http_response_code(400);
        $error = '요청을 확인해 주세요.';
    } elseif ($action === 'logout') {
        $_SESSION = [];
        session_destroy();
        $message = '로그아웃했습니다.';
    } elseif ($username === '' || $password === '') {
        $error = '아이디와 비밀번호를 입력해 주세요.';
    } elseif ($action === 'register') {
        if (strlen($username) > 64 || strlen($password) > 1024) {
            $error = '입력 길이를 확인해 주세요.';
        } else {
            try {
                $statement = $database->prepare('INSERT INTO users (username, password_hash) VALUES (?, ?)');
                $statement->execute([$username, password_hash($password, PASSWORD_DEFAULT)]);
                session_regenerate_id(true);
                $_SESSION['user_id'] = (int)$database->lastInsertId();
                $_SESSION['username'] = $username;
                $message = '회원가입했습니다.';
            } catch (PDOException $exception) {
                if ($exception->getCode() === '23000') {
                    $error = '이미 사용 중인 아이디입니다.';
                } else {
                    throw $exception;
                }
            }
        }
    } else {
        $statement = $database->prepare('SELECT id, username, password_hash FROM users WHERE username = ?');
        $statement->execute([$username]);
        $user = $statement->fetch(PDO::FETCH_ASSOC);
        if ($user && password_verify($password, $user['password_hash'])) {
            session_regenerate_id(true);
            $_SESSION['user_id'] = (int)$user['id'];
            $_SESSION['username'] = $user['username'];
            $message = '로그인했습니다.';
        } else {
            $error = '아이디 또는 비밀번호가 올바르지 않습니다.';
        }
    }
    }
}
$posts = $database->query('SELECT post_id, author, title, content FROM posts ORDER BY rowid DESC')->fetchAll(PDO::FETCH_ASSOC);

function escape(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
?>
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>회원 서비스</title>
  <style>
    body{font:16px system-ui,sans-serif;max-width:760px;margin:3rem auto;padding:0 1rem;color:#202820}
    h1{margin-bottom:.3rem}section{border:1px solid #ccd5ce;border-radius:8px;padding:1rem;margin:1rem 0}
    label{display:block;margin:.7rem 0}textarea{display:block;width:100%;box-sizing:border-box;padding:.6rem;margin-top:.25rem}input{display:block;width:100%;box-sizing:border-box;padding:.6rem;margin-top:.25rem}
    button{padding:.55rem .9rem;cursor:pointer}.error{color:#a21d24}.message{color:#176b32}
  </style>
</head>
<body>
  <h1>회원 서비스</h1>
  <?php if ($error !== ''): ?><p class="error"><?= escape($error) ?></p><?php endif; ?>
  <?php if ($profile !== null): ?>
    <section>
      <h2>마이페이지</h2>
      <p>User name: <?= escape($profile['user_name']) ?></p>
      <p>Email: <?= escape($profile['email']) ?></p>
      <p>Bio: <?= escape($profile['bio']) ?></p>
    </section>
    <p><a href="/">게시판으로 돌아가기</a></p>
  <?php elseif ($path === '/report' && isset($_SESSION['user_id'])): ?>
    <header>
      <p><?= escape($_SESSION['username']) ?>님, 로그인했습니다.</p>
      <p><a href="/">게시판으로 돌아가기</a></p>
    </header>
    <?php if ($reportMessage !== ''): ?><p class="message"><?= escape($reportMessage) ?></p><?php endif; ?>
    <?php if ($reportSummary !== null): ?>
      <p>관리자 이메일: <?= escape($reportSummary['email']) ?> · 게시글 ID: <?= (int)$reportSummary['post_id'] ?></p>
    <?php endif; ?>
    <section>
      <h2>게시글 신고</h2>
      <form method="post" action="/report">
        <input type="hidden" name="action" value="submit_report">
        <label>관리자 이메일<input name="admin_email" type="email" required></label>
        <label>게시글 ID<input name="post_id" type="number" min="1" required></label>
        <button>신고 제출</button>
      </form>
    </section>
  <?php elseif (isset($_SESSION['user_id'])): ?>
    <header>
      <p><?= escape($_SESSION['username']) ?>님, 로그인했습니다. (ID: <?= (int)$_SESSION['user_id'] ?>)</p>
      <form method="post"><input type="hidden" name="action" value="logout"><button>로그아웃</button></form>
    </header>
    <?php if ($message !== ''): ?><p class="message"><?= escape($message) ?></p><?php endif; ?>
    <p><a href="/report">게시글 신고</a></p>
    <section>
      <h2>게시글 작성</h2>
      <form method="post" action="/">
        <input type="hidden" name="action" value="create_post">
        <label>제목<input name="title" maxlength="200" required></label>
        <label>내용<textarea name="content" rows="5" maxlength="10000" required></textarea></label>
        <button>등록</button>
      </form>
    </section>
    <h2>게시판</h2>
    <?php foreach ($posts as $post): ?>
      <section>
        <small>#<?= (int)$post['post_id'] ?> · <?= escape($post['author']) ?></small>
        <h3><?= escape($post['title']) ?></h3>
        <div><?= $post['content'] ?></div>
      </section>
    <?php endforeach; ?>
  <?php else: ?>
    <?php if ($error !== ''): ?><p class="error"><?= escape($error) ?></p><?php endif; ?>
    <?php if ($message !== ''): ?><p class="message"><?= escape($message) ?></p><?php endif; ?>
    <section>
      <h2>회원가입</h2>
      <form method="post">
        <input type="hidden" name="action" value="register">
        <label>아이디<input name="username" maxlength="64" required autocomplete="username"></label>
        <label>비밀번호<input name="password" type="password" maxlength="1024" required autocomplete="new-password"></label>
        <button>가입</button>
      </form>
    </section>
    <section>
      <h2>로그인</h2>
      <form method="post">
        <input type="hidden" name="action" value="login">
        <label>아이디<input name="username" maxlength="64" required autocomplete="username"></label>
        <label>비밀번호<input name="password" type="password" maxlength="1024" required autocomplete="current-password"></label>
        <button>로그인</button>
      </form>
    </section>
  <?php endif; ?>
</body>
</html>
