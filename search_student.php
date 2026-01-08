<?php
// Database connection
$servername = "localhost";
$username = "root";
$password = "";
$dbname = "school";

$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Get roll number from request
$roll_number = intval($_GET['roll_number']);

// Prepare and execute SQL statement
$stmt = $conn->prepare("SELECT name, age, class FROM students WHERE roll_number = ?");
$stmt->bind_param("i", $roll_number);
$stmt->execute();
$stmt->store_result();

// Check if student is found
if ($stmt->num_rows > 0) {
    $stmt->bind_result($name, $age, $class);
    $stmt->fetch();
    echo json_encode([
        'status' => 'success',
        'data' => [
            'name' => $name,
            'age' => $age,
            'class' => $class
        ]
    ]);
} else {
    echo json_encode([
        'status' => 'error',
        'message' => 'Student not found'
    ]);
}

$stmt->close();
$conn->close();