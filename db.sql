CREATE DATABASE school;

USE school;

CREATE TABLE students (
    roll_number INT PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    class VARCHAR(50)
);

INSERT INTO students (roll_number, name, age, class) VALUES
(1, 'Alice', 15, '10th Grade'),
(2, 'Bob', 16, '11th Grade');
