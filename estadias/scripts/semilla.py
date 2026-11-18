"""Carga datos de prueba (usuarios de cada rol, grupos, requisitos y algunas entregas).

Uso:  python -m scripts.semilla            (solo si la BD está vacía)
      python -m scripts.semilla --forzar   (agrega aunque ya existan usuarios)
"""
import sys
import uuid

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import (
    APROBADO,
    CORRECCION,
    EN_REVISION,
    ROL_ADMIN,
    ROL_ALUMNO,
    ROL_PROFESOR,
    TIPO_ESPECIFICO,
    TIPO_GENERAL,
    Alumno,
    Categoria,
    Entrega,
    Grupo,
    ProyectoEntrega,
    Requisito,
    Revision,
    Usuario,
)
from app.security import hash_password

# Credenciales SOLO para pruebas locales. Cámbialas o desactiva estas cuentas en producción.
USUARIOS_PRUEBA = {
    "admin": ("Encargada de Estadías (prueba)", "admin@estadias.test", "Admin2026"),
    "profesor1": ("Profesor Uno (prueba)", "profesor1@estadias.test", "Profesor2026"),
    "profesor2": ("Profesora Dos (prueba)", "profesor2@estadias.test", "Profesor2026"),
}
ALUMNOS_PRUEBA = [
    # nombre, email, matrícula, carrera, grupo, profesor
    ("Alumno A Uno (prueba)", "alumno1@estadias.test", "A0001", "Ingeniería en Sistemas", "Grupo A", "profesor1"),
    ("Alumno A Dos (prueba)", "alumno2@estadias.test", "A0002", "Ingeniería en Sistemas", "Grupo A", "profesor1"),
    ("Alumno B Uno (prueba)", "alumno3@estadias.test", "B0001", "Ingeniería Industrial", "Grupo B", "profesor2"),
    ("Alumno C Uno (prueba)", "alumno4@estadias.test", "C0001", "Administración", "Grupo C", None),
]
PASSWORD_ALUMNO = "Alumno2026"


def pdf_minimo(texto: str) -> bytes:
    """Genera un PDF válido de una página con un texto (para entregas de ejemplo)."""
    contenido = f"BT /F1 18 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1", "replace")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(contenido) + contenido + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    salida = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objetos, 1):
        offsets.append(len(salida))
        salida += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        salida += f"{off:010d} 00000 n \n".encode()
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(salida)


def guardar_pdf(sub: str, texto: str) -> tuple[str, int]:
    datos = pdf_minimo(texto)
    rel = f"{sub}/{uuid.uuid4().hex}.pdf"
    destino = settings.STORAGE_DIR / rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)
    return rel, len(datos)


def main(forzar: bool = False) -> None:
    db = SessionLocal()
    if db.scalar(select(Usuario.id).limit(1)) and not forzar:
        print("La base de datos ya tiene usuarios; no se cargó nada (usa --forzar).")
        return

    u = {}
    for clave, (nombre, email, pw) in USUARIOS_PRUEBA.items():
        rol = ROL_ADMIN if clave == "admin" else ROL_PROFESOR
        u[clave] = Usuario(nombre=nombre, email=email, password_hash=hash_password(pw), rol=rol)
        db.add(u[clave])

    grupos = {n: Grupo(nombre=n, descripcion=d) for n, d in [
        ("Grupo A", "Estadía en empresas de tecnología"),
        ("Grupo B", "Estadía en sector industrial"),
        ("Grupo C", "Estadía en sector servicios"),
    ]}
    db.add_all(grupos.values())

    cats = {n: Categoria(nombre=n, orden=i) for i, n in enumerate(
        ["Documentación personal", "Documentación académica", "Documentación empresarial", "Documentación administrativa"], 1)}
    db.add_all(cats.values())
    db.flush()

    reqs = [
        Requisito(categoria=cats["Documentación personal"], nombre="Identificación oficial", descripcion="INE o pasaporte vigente, por ambos lados.", tipo=TIPO_GENERAL),
        Requisito(categoria=cats["Documentación personal"], nombre="Comprobante de domicilio", descripcion="No mayor a 3 meses.", tipo=TIPO_GENERAL),
        Requisito(categoria=cats["Documentación académica"], nombre="Historial académico", tipo=TIPO_GENERAL),
        Requisito(categoria=cats["Documentación empresarial"], nombre="Carta de aceptación", descripcion="Firmada y sellada por la empresa.", tipo=TIPO_GENERAL),
        Requisito(categoria=cats["Documentación administrativa"], nombre="Convenio de estadía", tipo=TIPO_ESPECIFICO, grupos=[grupos["Grupo A"]]),
        Requisito(categoria=cats["Documentación administrativa"], nombre="Seguro facultativo", tipo=TIPO_ESPECIFICO, grupos=[grupos["Grupo B"]]),
    ]
    db.add_all(reqs)
    db.flush()

    alumnos = []
    for nombre, email, mat, carrera, grupo, prof in ALUMNOS_PRUEBA:
        usr = Usuario(nombre=nombre, email=email, password_hash=hash_password(PASSWORD_ALUMNO), rol=ROL_ALUMNO)
        a = Alumno(usuario=usr, matricula=mat, carrera=carrera, grupo=grupos[grupo], profesor=u[prof] if prof else None)
        db.add(a)
        alumnos.append(a)
    db.flush()

    # Entregas de ejemplo para el alumno 1: una aprobada, una con corrección (2 versiones) y una en revisión
    a1 = alumnos[0]
    def entrega(alumno, req, version, estado, texto):
        ruta, tam = guardar_pdf(f"entregas/{alumno.id}", texto)
        e = Entrega(alumno=alumno, requisito=req, version=version, ruta=ruta, nombre_original=f"{req.nombre}.pdf",
                    mime="application/pdf", tamano=tam, estado=estado)
        db.add(e)
        db.flush()
        return e

    e = entrega(a1, reqs[0], 1, APROBADO, "Identificacion oficial - ejemplo")
    db.add(Revision(entrega=e, revisor=u["admin"], resultado=APROBADO, observacion="Correcto."))
    e = entrega(a1, reqs[1], 1, CORRECCION, "Comprobante de domicilio - ejemplo antiguo")
    db.add(Revision(entrega=e, revisor=u["admin"], resultado=CORRECCION, observacion="El comprobante tiene más de 3 meses; sube uno reciente."))
    entrega(a1, reqs[2], 1, EN_REVISION, "Historial academico - ejemplo")
    entrega(alumnos[2], reqs[0], 1, EN_REVISION, "Identificacion oficial B - ejemplo")

    ruta, tam = guardar_pdf(f"proyectos/{a1.id}", "Proyecto de estadia - version 1")
    db.add(ProyectoEntrega(alumno=a1, version=1, titulo="Sistema de control de inventarios", ruta=ruta,
                           nombre_original="proyecto_v1.pdf", mime="application/pdf", tamano=tam, estado=EN_REVISION))
    db.commit()
    print("Datos de prueba cargados. Credenciales en README.md (sección «Usuarios de prueba»).")


if __name__ == "__main__":
    main(forzar="--forzar" in sys.argv)
