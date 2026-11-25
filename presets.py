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


# Ready-to-trace systems, kept out of the exercise generator's component catalogue.
BENCH_PRESETS = {
    'Telescopio refractor kepleriano · lentes delgadas': {
        'elements': [
            Element(name='Objetivo', kind='Lente delgada convergente', position=0.,
                    focal_length=200., aperture=40., thickness=0.),
            Element(name='Ocular', kind='Lente delgada convergente', position=240.,
                    focal_length=40., aperture=16., thickness=0.),
        ],
        'aperture_position': -10., 'aperture_diameter': 40.,
        'ray_model': 'Paraxial · lente delgada',
    },
    'Telescopio newtoniano': {
        'elements': [
            Element(name='Primario', kind='Espejo parabólico', position=500.,
                    r1=200., aperture=40., thickness=0.),
            Element(name='Secundario', kind='Espejo plano', position=425., tilt=45.,
                    aperture=12., thickness=0., invert_mirror=True),
            Element(name='Ocular', kind='Lente delgada convergente', position=425.,
                    height=50., tilt=90., focal_length=25., aperture=20., thickness=0.),
        ],
        'aperture_position': 0., 'aperture_diameter': 40.,
        'ray_model': 'Exacto · Snell y reflexión',
    },
    'Telescopio Ritchey–Chrétien': {
        'elements': [
            Element(name='Primario', kind='Espejo hiperbólico cóncavo con abertura central',
                    position=4906.072/12, r1=920., conic_constant=-1.0022985,
                    aperture=200., central_opening=50., thickness=0.),
            Element(name='Secundario', kind='Espejo hiperbólico convexo', position=0.,
                    r1=1358./12, conic_constant=-1.496, aperture=281./12,
                    thickness=0., invert_mirror=True),
        ],
        'aperture_position': -20., 'aperture_diameter': 200.,
        'ray_model': 'Exacto · Snell y reflexión',
    },
    'Teleobjetivo fotográfico · 250 mm': {
        'elements': [
            Element(name='Grupo delantero', kind='Lente delgada convergente', position=0.,
                    focal_length=100., aperture=32., thickness=0.),
            Element(name='Grupo trasero', kind='Lente delgada divergente', position=70.,
                    focal_length=50., aperture=14., thickness=0.),
        ],
        'aperture_position': -10., 'aperture_diameter': 32.,
        'ray_model': 'Paraxial · lente delgada',
    },
}
