-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: 127.0.0.1    Database: estadias
-- ------------------------------------------------------
-- Server version	10.4.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES ('1662b5ea8542');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alumnos`
--

DROP TABLE IF EXISTS `alumnos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `alumnos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `usuario_id` int(11) NOT NULL,
  `matricula` varchar(30) NOT NULL,
  `carrera` varchar(150) NOT NULL,
  `telefono` varchar(30) DEFAULT NULL,
  `grupo_id` int(11) DEFAULT NULL,
  `profesor_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `matricula` (`matricula`),
  UNIQUE KEY `usuario_id` (`usuario_id`),
  KEY `ix_alumnos_grupo_id` (`grupo_id`),
  KEY `ix_alumnos_profesor_id` (`profesor_id`),
  CONSTRAINT `alumnos_ibfk_1` FOREIGN KEY (`grupo_id`) REFERENCES `grupos` (`id`),
  CONSTRAINT `alumnos_ibfk_2` FOREIGN KEY (`profesor_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `alumnos_ibfk_3` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alumnos`
--

LOCK TABLES `alumnos` WRITE;
/*!40000 ALTER TABLE `alumnos` DISABLE KEYS */;
INSERT INTO `alumnos` VALUES (1,4,'A0001','Ingeniería en Sistemas',NULL,1,2),(2,5,'A0002','Ingeniería en Sistemas',NULL,1,2),(3,6,'B0001','Ingeniería Industrial',NULL,2,3),(4,7,'C0001','Administración',NULL,3,NULL);
/*!40000 ALTER TABLE `alumnos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bitacora`
--

DROP TABLE IF EXISTS `bitacora`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `bitacora` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `usuario_id` int(11) DEFAULT NULL,
  `accion` varchar(60) NOT NULL,
  `detalle` varchar(500) DEFAULT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `creado_en` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_bitacora_accion` (`accion`),
  KEY `ix_bitacora_creado_en` (`creado_en`),
  KEY `ix_bitacora_usuario_id` (`usuario_id`),
  CONSTRAINT `bitacora_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bitacora`
--

LOCK TABLES `bitacora` WRITE;
/*!40000 ALTER TABLE `bitacora` DISABLE KEYS */;
/*!40000 ALTER TABLE `bitacora` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `categorias`
--

DROP TABLE IF EXISTS `categorias`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `categorias` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(120) NOT NULL,
  `orden` int(11) NOT NULL,
  `activo` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `categorias`
--

LOCK TABLES `categorias` WRITE;
/*!40000 ALTER TABLE `categorias` DISABLE KEYS */;
INSERT INTO `categorias` VALUES (1,'Documentación personal',1,1),(2,'Documentación académica',2,1),(3,'Documentación empresarial',3,1),(4,'Documentación administrativa',4,1);
/*!40000 ALTER TABLE `categorias` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `entregas`
--

DROP TABLE IF EXISTS `entregas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `entregas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `alumno_id` int(11) NOT NULL,
  `requisito_id` int(11) NOT NULL,
  `version` int(11) NOT NULL,
  `ruta` varchar(255) NOT NULL,
  `nombre_original` varchar(255) NOT NULL,
  `mime` varchar(50) NOT NULL,
  `tamano` int(11) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `creado_en` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_entrega_version` (`alumno_id`,`requisito_id`,`version`),
  KEY `requisito_id` (`requisito_id`),
  KEY `ix_entregas_alumno_requisito` (`alumno_id`,`requisito_id`),
  KEY `ix_entregas_estado` (`estado`),
  CONSTRAINT `entregas_ibfk_1` FOREIGN KEY (`alumno_id`) REFERENCES `alumnos` (`id`),
  CONSTRAINT `entregas_ibfk_2` FOREIGN KEY (`requisito_id`) REFERENCES `requisitos` (`id`),
  CONSTRAINT `ck_entregas_estado` CHECK (`estado` in ('en_revision','aprobado','correccion'))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `entregas`
--

LOCK TABLES `entregas` WRITE;
/*!40000 ALTER TABLE `entregas` DISABLE KEYS */;
INSERT INTO `entregas` VALUES (1,1,1,1,'entregas/1/af4c7c45b3014428991a3aa078a93c67.pdf','Identificación oficial.pdf','application/pdf',607,'aprobado','2026-11-11 16:23:40'),(2,1,2,1,'entregas/1/fc1a9c36d8eb4457a1519a57fd20725a.pdf','Comprobante de domicilio.pdf','application/pdf',617,'correccion','2026-11-11 16:23:40'),(3,1,3,1,'entregas/1/4cf1c0c7f42e4c1ab09c8f360d86dc68.pdf','Historial académico.pdf','application/pdf',604,'en_revision','2026-11-11 16:23:40'),(4,3,1,1,'entregas/3/0c5cdce411484df89bda982e7e6af588.pdf','Identificación oficial.pdf','application/pdf',609,'en_revision','2026-11-11 16:23:40');
/*!40000 ALTER TABLE `entregas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `grupos`
--

DROP TABLE IF EXISTS `grupos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `grupos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `grupos`
--

LOCK TABLES `grupos` WRITE;
/*!40000 ALTER TABLE `grupos` DISABLE KEYS */;
INSERT INTO `grupos` VALUES (1,'Grupo A','Estadía en empresas de tecnología',1),(2,'Grupo B','Estadía en sector industrial',1),(3,'Grupo C','Estadía en sector servicios',1);
/*!40000 ALTER TABLE `grupos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `proyecto_entregas`
--

DROP TABLE IF EXISTS `proyecto_entregas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `proyecto_entregas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `alumno_id` int(11) NOT NULL,
  `version` int(11) NOT NULL,
  `titulo` varchar(255) NOT NULL,
  `ruta` varchar(255) NOT NULL,
  `nombre_original` varchar(255) NOT NULL,
  `mime` varchar(50) NOT NULL,
  `tamano` int(11) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `creado_en` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_proyecto_version` (`alumno_id`,`version`),
  KEY `ix_proyecto_entregas_estado` (`estado`),
  CONSTRAINT `proyecto_entregas_ibfk_1` FOREIGN KEY (`alumno_id`) REFERENCES `alumnos` (`id`),
  CONSTRAINT `ck_proyecto_estado` CHECK (`estado` in ('en_revision','aprobado','correccion','rechazado'))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `proyecto_entregas`
--

LOCK TABLES `proyecto_entregas` WRITE;
/*!40000 ALTER TABLE `proyecto_entregas` DISABLE KEYS */;
INSERT INTO `proyecto_entregas` VALUES (1,1,1,'Sistema de control de inventarios','proyectos/1/ad4bb67fd41549c9a754c22c73eae953.pdf','proyecto_v1.pdf','application/pdf',606,'en_revision','2026-11-11 16:23:40');
/*!40000 ALTER TABLE `proyecto_entregas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `requisito_grupo`
--

DROP TABLE IF EXISTS `requisito_grupo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `requisito_grupo` (
  `requisito_id` int(11) NOT NULL,
  `grupo_id` int(11) NOT NULL,
  PRIMARY KEY (`requisito_id`,`grupo_id`),
  KEY `grupo_id` (`grupo_id`),
  CONSTRAINT `requisito_grupo_ibfk_1` FOREIGN KEY (`grupo_id`) REFERENCES `grupos` (`id`),
  CONSTRAINT `requisito_grupo_ibfk_2` FOREIGN KEY (`requisito_id`) REFERENCES `requisitos` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `requisito_grupo`
--

LOCK TABLES `requisito_grupo` WRITE;
/*!40000 ALTER TABLE `requisito_grupo` DISABLE KEYS */;
INSERT INTO `requisito_grupo` VALUES (5,1),(6,2);
/*!40000 ALTER TABLE `requisito_grupo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `requisitos`
--

DROP TABLE IF EXISTS `requisitos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `requisitos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `categoria_id` int(11) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `descripcion` varchar(500) DEFAULT NULL,
  `tipo` varchar(20) NOT NULL,
  `activo` tinyint(1) NOT NULL,
  `creado_en` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_requisitos_categoria_id` (`categoria_id`),
  CONSTRAINT `requisitos_ibfk_1` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`),
  CONSTRAINT `ck_requisitos_tipo` CHECK (`tipo` in ('general','especifico'))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `requisitos`
--

LOCK TABLES `requisitos` WRITE;
/*!40000 ALTER TABLE `requisitos` DISABLE KEYS */;
INSERT INTO `requisitos` VALUES (1,1,'Identificación oficial','INE o pasaporte vigente, por ambos lados.','general',1,'2026-11-11 16:23:38'),(2,1,'Comprobante de domicilio','No mayor a 3 meses.','general',1,'2026-11-11 16:23:38'),(3,2,'Historial académico',NULL,'general',1,'2026-11-11 16:23:38'),(4,3,'Carta de aceptación','Firmada y sellada por la empresa.','general',1,'2026-11-11 16:23:38'),(5,4,'Convenio de estadía',NULL,'especifico',1,'2026-11-11 16:23:38'),(6,4,'Seguro facultativo',NULL,'especifico',1,'2026-11-11 16:23:38');
/*!40000 ALTER TABLE `requisitos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `revisiones`
--

DROP TABLE IF EXISTS `revisiones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `revisiones` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `entrega_id` int(11) DEFAULT NULL,
  `proyecto_entrega_id` int(11) DEFAULT NULL,
  `revisor_id` int(11) NOT NULL,
  `resultado` varchar(20) NOT NULL,
  `observacion` text DEFAULT NULL,
  `creado_en` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `revisor_id` (`revisor_id`),
  KEY `ix_revisiones_entrega_id` (`entrega_id`),
  KEY `ix_revisiones_proyecto_entrega_id` (`proyecto_entrega_id`),
  CONSTRAINT `revisiones_ibfk_1` FOREIGN KEY (`entrega_id`) REFERENCES `entregas` (`id`),
  CONSTRAINT `revisiones_ibfk_2` FOREIGN KEY (`proyecto_entrega_id`) REFERENCES `proyecto_entregas` (`id`),
  CONSTRAINT `revisiones_ibfk_3` FOREIGN KEY (`revisor_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `ck_revision_destino` CHECK (`entrega_id` is null <> (`proyecto_entrega_id` is null))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `revisiones`
--

LOCK TABLES `revisiones` WRITE;
/*!40000 ALTER TABLE `revisiones` DISABLE KEYS */;
INSERT INTO `revisiones` VALUES (1,1,NULL,1,'aprobado','Correcto.','2026-11-11 16:23:40'),(2,2,NULL,1,'correccion','El comprobante tiene más de 3 meses; sube uno reciente.','2026-11-11 16:23:40');
/*!40000 ALTER TABLE `revisiones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(150) NOT NULL,
  `email` varchar(190) NOT NULL,
  `password_hash` varchar(100) NOT NULL,
  `rol` varchar(20) NOT NULL,
  `activo` tinyint(1) NOT NULL,
  `creado_en` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `ix_usuarios_rol` (`rol`),
  CONSTRAINT `ck_usuarios_rol` CHECK (`rol` in ('admin','profesor','alumno'))
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (1,'Encargada de Estadías (prueba)','admin@estadias.test','$2b$12$lnlixhXRbpxG/VnPez0QR..jkssQVu2xnMcQSCI9QnRMlm1s8bWmS','admin',1,'2026-11-11 16:23:38'),(2,'Profesor Uno (prueba)','profesor1@estadias.test','$2b$12$taGWHdMNCR8cHBEOdeIRKOxcjKG3OoWONeJYeeU8/Acj/cExpqgji','profesor',1,'2026-11-11 16:23:38'),(3,'Profesora Dos (prueba)','profesor2@estadias.test','$2b$12$zbt/WlVuU/Wnt59CcjndA.FlsdH2B3F4RBtr99iwSyWqlAVlb5/Bi','profesor',1,'2026-11-11 16:23:38'),(4,'Alumno A Uno (prueba)','alumno1@estadias.test','$2b$12$DUvU/nl5NJjL3wSREt3hTOrE3CLXxYJo43jTZDSi0saDMWkvJMhuO','alumno',1,'2026-11-11 16:23:40'),(5,'Alumno A Dos (prueba)','alumno2@estadias.test','$2b$12$QUQIEqb6IoPBr0zy8veT2edLbI2mkdCNgjrc8eogZKGjINZKaJkIu','alumno',1,'2026-11-11 16:23:40'),(6,'Alumno B Uno (prueba)','alumno3@estadias.test','$2b$12$XsvN9t1/X/Tr4lawfjO5XOklVVtqWxQiaVfRzWceIxWPt3BSxjqEK','alumno',1,'2026-11-11 16:23:40'),(7,'Alumno C Uno (prueba)','alumno4@estadias.test','$2b$12$1LdTpiUrv9kW5QnophBvI.gLzy5fej4./O6hZWhtQ8x5QoYuOYxpq','alumno',1,'2026-11-11 16:23:40');
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'estadias'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-11 16:23:50
