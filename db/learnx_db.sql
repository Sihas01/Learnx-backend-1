-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jan 08, 2026 at 04:44 AM
-- Server version: 12.1.2-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `learnx_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `firstName` varchar(100) DEFAULT NULL,
  `lastName` varchar(100) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `studentId` varchar(50) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `reset_token` varchar(255) DEFAULT NULL,
  `is_verified` int(11) NOT NULL DEFAULT 0,
  `verification_token` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `firstName`, `lastName`, `email`, `studentId`, `password`, `reset_token`, `is_verified`, `verification_token`) VALUES
(1, 'John', 'Doe', 'john@example.com', 'RET123', 'password123', NULL, 0, NULL),
(2, 'John2', 'Doe', 'john@example2.com', 'RET1234', 'password123', NULL, 0, NULL),
(5, 'John', 'Doe', 'john@exampl2e.com', 'RET1238', 'cGFzc3dvcmQxMjM=', NULL, 0, NULL),
(6, 'Saman', 'Kumara', 'your.email+fakedata14069@gmail.com', 'RET2536', 'V2VOb21GN1BsckU4Ykxi', NULL, 0, NULL),
(7, '', '', '', '', '', NULL, 0, NULL),
(8, 'john', 'Doe2', 'hogn@gmail.com', '12345', 'MTIzNDU2Nzg=', NULL, 0, NULL),
(9, 'ko', 'm', 'ko@gmail.com', '45678', 'UzEyMzQ1QHF3', NULL, 0, NULL),
(10, 'lok', 'io', 'io@gmai.com', '456789', 'MTIzUDExN3BA', NULL, 0, NULL),
(11, 'Percy', 'Jackson', 'kelav54554@24faw.com', 'RET4567', 'MTIzNDU2NzhRQA==', '4db99ea163e441158ba64dfee3ef54b9', 0, NULL),
(13, 'Kevin', 'John', 'bawol39812@24faw.com', 'RE2345', 'MTIzNDU2NzhRIQ==', NULL, 1, NULL),
(14, 'Praesentium quia architecto dolor error.', '2025-08-20 17:10:15', 'jopima4188@cameltok.com', 'RE34567', 'VUNrR3I3QmQ2RmFobjlBIQ==', NULL, 1, NULL);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD UNIQUE KEY `studentId` (`studentId`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
