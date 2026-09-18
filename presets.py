"""Shared example catalogue for the simulator and exercise generator."""
from optics import Element

PRESETS = {
    'Lente convergente': [Element(index=1.5)],
    'Lente divergente': [Element(kind='Bicóncava', index=1.5)],
    'Dos lentes y diafragma': [Element(name='Objetivo', index=1.5), Element(name='Stop', kind='Diafragma', position=65, aperture=8, thickness=2), Element(name='Ocular', position=100, aperture=20, thickness=5, index=1.5, r1=35, r2=-35)],
    'Espejo plano': [Element(name='Espejo plano', kind='Espejo plano', position=50, aperture=40, thickness=0)],
    'Lente y espejo (doble paso)': [Element(index=1.5), Element(name='Espejo', kind='Espejo plano', position=100, aperture=40, thickness=0)],
    'Espejo cóncavo': [Element(name='Espejo', kind='Espejo cóncavo', position=50, aperture=25, thickness=0, r1=100)],
    'Edmund PCX · BFL ≈ 47,48 mm': [Element(name='PCX 49-849', kind='Convexa-plana', position=25, aperture=25.4, thickness=5, index=1.517, r1=26.25)],
    'Banco vacío': [],
}
