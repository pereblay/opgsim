"""Óptica gaussiana centrada. Unidades: mm, radianes; estado (y, n*theta)."""
from dataclasses import dataclass
import math
import numpy as np

TYPES = ['Biconvexa', 'Bicóncava', 'Plano-convexa', 'Plano-cóncava', 'Convexa-plana', 'Cóncava-plana',
         'Menisco', 'Lente personalizada', 'Espejo plano', 'Espejo cóncavo',
         'Espejo convexo', 'Diafragma']
EPS = 1e-10

@dataclass
class Element:
    name: str = 'Lente'
    kind: str = 'Biconvexa'
    position: float = 40.0
    aperture: float = 20.0
    thickness: float = 4.0
    index: float = 1.0
    r1: float = 50.0
    r2: float = -50.0
    dispersion: float = 0.0  # Cauchy B, µm²; n is specified at 550 nm

    def radii(self):
        a, b = abs(self.r1), abs(self.r2)
        return {'Biconvexa': (a, -b), 'Bicóncava': (-a, b),
                'Plano-convexa': (math.inf, -b), 'Plano-cóncava': (math.inf, b),
                'Convexa-plana': (a, math.inf), 'Cóncava-plana': (-a, math.inf),
                'Menisco': (a, b)}.get(self.kind, (self.r1, self.r2))

    @property
    def clear_aperture(self):
        """Trim the spherical caps at their domain or first mutual intersection."""
        radii = self.radii() if self.lens else (() if self.kind in ('Diafragma', 'Espejo plano') else (self.r1,))
        if any(math.isnan(r) or r == 0 for r in radii):
            raise ValueError(f'{self.name}: los radios deben ser distintos de cero.')
        limit = min([self.aperture/2] + [abs(r) for r in radii])
        if self.lens:
            r1, r2 = radii
            def width(y):
                return self.thickness + float(sag(r2, y)) - float(sag(r1, y))
            if width(limit) < 0:
                low, high = 0., limit
                for _ in range(64):
                    mid = (low+high)/2
                    if width(mid) >= 0:
                        low = mid
                    else:
                        high = mid
                limit = low
        return 2*limit

    def n(self, wavelength):
        return self.index + self.dispersion * ((1000 / wavelength)**2 - (1 / .55)**2)

    @property
    def lens(self):
        return not (self.kind.startswith('Espejo') or self.kind == 'Diafragma')

@dataclass
class Surface:
    x: float
    aperture: float
    matrix: np.ndarray
    name: str
    n_after: float
    kind: str = 'refraction'


def translation(distance, n=1.):
    return np.array([[1., distance/n], [0., 1.]])


def refraction(n1, n2, radius):
    return np.array([[1., 0.], [0. if math.isinf(radius) else -(n2-n1)/radius, 1.]])


def sag(radius, y):
    if math.isinf(radius):
        return np.zeros_like(y)
    # Rationalized spherical sag avoids subtracting nearly equal large radii.
    y = np.asarray(y)
    return (y/radius)*y / (1 + np.sqrt(np.maximum(0., 1 - (y/radius)**2)))


def build(elements, diameter, wavelength):
    if not math.isfinite(diameter) or diameter <= 0:
        raise ValueError('La abertura inicial debe ser positiva.')
    if not math.isfinite(wavelength) or wavelength <= 0:
        raise ValueError('La longitud de onda debe ser positiva.')
    surfaces = [Surface(0., diameter, np.eye(2), 'Abertura inicial', 1., 'stop')]
    last = 0.
    for e in sorted(elements, key=lambda e: e.position):
        vals = [e.position, e.aperture, e.thickness, e.index, e.dispersion]
        if not all(math.isfinite(v) for v in vals):
            raise ValueError(f'{e.name}: hay valores no finitos.')
        if e.kind not in TYPES or e.position < last or e.aperture <= 0 or e.thickness < 0:
            raise ValueError(f'{e.name}: tipo inválido, abertura no positiva, posición negativa o elementos solapados.')
        if e.lens:
            n = e.n(wavelength)
            if n < 1 or e.index < 1:
                raise ValueError(f'{e.name}: el índice debe ser ≥ 1 también a la longitud de onda elegida.')
            r1, r2 = e.radii()
            aperture = e.clear_aperture
            surfaces += [Surface(e.position, aperture, refraction(1, n, r1), e.name+' · cara 1', n),
                         Surface(e.position+e.thickness, aperture, refraction(n, 1, r2), e.name+' · cara 2', 1.)]
            last = e.position + e.thickness
        else:
            power = 0.
            if e.kind != 'Espejo plano' and e.kind.startswith('Espejo'):
                if not math.isfinite(e.r1) or e.r1 == 0:
                    raise ValueError(f'{e.name}: radio de espejo insuficiente.')
                power = (-2 if e.kind == 'Espejo cóncavo' else 2)/abs(e.r1)
            surfaces.append(Surface(e.position, e.clear_aperture, np.array([[1., 0.], [power, 1.]]), e.name, 1., 'mirror' if e.kind.startswith('Espejo') else 'stop'))
            last = e.position
            if e.kind == 'Diafragma' and e.thickness > 0:
                last += e.thickness
                surfaces.append(Surface(last, e.aperture, np.eye(2), e.name+' · salida', 1., 'stop'))
    return surfaces


def matrices(surfaces):
    pre, post = [], []
    m, x, n = np.eye(2), 0., 1.
    for s in surfaces:
        m = translation(s.x-x, n) @ m
        pre.append(m.copy())
        m = s.matrix @ m
        post.append(m.copy())
        x, n = s.x, s.n_after
    return pre, post


def matrix_walkthrough(surfaces, height, theta, start_x=0.):
    """Transfer in (height, theta), with local forward angle on reflected paths.

    The input medium is air. Surfaces use the unfolded axial coordinate.
    Aperture clipping is reported separately: ABCD itself remains linear.
    """
    state = np.array([height, theta], dtype=float)
    total = np.eye(2)
    x, n = start_x, 1.
    rows = []
    clipped = False
    for surface in surfaces:
        distance = surface.x-x
        propagation = np.array([[1., distance], [0., 1.]])
        interface = np.diag([1., 1/surface.n_after]) @ surface.matrix @ np.diag([1., n])
        at_surface = propagation @ state
        clipped = clipped or abs(at_surface[0]) > surface.aperture/2+1e-8
        step = interface @ propagation
        state = step @ state
        total = step @ total
        rows.append(dict(name=surface.name, distance=distance, n_before=n, n_after=surface.n_after,
                         propagation=propagation, interface=interface, matrix=step,
                         height=float(state[0]), theta=float(state[1]), clipped=clipped))
        x, n = surface.x, surface.n_after
    return total, state, rows


def conjugate(m, x):
    """Image of an input plane, output medium air. None means infinity."""
    if abs(m[1, 1]) < EPS:
        return None, None
    distance = -m[0, 1]/m[1, 1]
    return float(x+distance), float(np.linalg.det(m)/m[1, 1])


def analyze(surfaces, object_x):
    # None denotes an axial object at infinity; positive coordinates can
    # describe a virtual incident object (e.g. the front focus of a diverger).
    if object_x is not None and not math.isfinite(object_x):
        raise ValueError('La coordenada del objeto debe ser finita, o None para infinito.')
    pre, post = matrices(surfaces)
    m = post[-1]
    total = m if object_x is None else m @ translation(-object_x)
    if object_x is None:
        image_x = None if abs(m[1, 0]) < EPS else float(surfaces[-1].x-m[0, 0]/m[1, 0])
        magnification = None
    else:
        image_x, magnification = conjugate(total, surfaces[-1].x)
    basis = np.array([1., 0.]) if object_x is None else np.array([-object_x, 1.])
    limits = [s.aperture/(2*abs((p @ basis)[0]))
              if abs((p @ basis)[0]) > EPS else math.inf
              for s, p in zip(surfaces, pre)]
    stop = int(np.argmin(limits))
    # Entrance pupil = backward image of stop through preceding optics.
    entrance_x, entrance_mag = conjugate(np.linalg.inv(pre[stop]), 0.)
    downstream = m @ np.linalg.inv(pre[stop])
    exit_x, exit_mag = conjugate(downstream, surfaces[-1].x)
    c = m[1, 0]
    focal = None if abs(c) < EPS else float(-1/c)
    return dict(matrix=m, pre=pre, post=post, image_x=image_x, magnification=magnification,
                stop=stop, entrance_x=entrance_x,
                entrance_diameter=None if entrance_mag is None else abs(entrance_mag)*surfaces[stop].aperture,
                exit_x=exit_x, exit_diameter=None if exit_mag is None else abs(exit_mag)*surfaces[stop].aperture,
                focal=focal, back_focus=None if focal is None else float(-m[0,0]/c),
                front_focus=None if focal is None else float(m[1,1]/c),
                h1=None if focal is None else float((m[1,1]-1)/c),
                h2=None if focal is None else float(surfaces[-1].x+(1-m[0,0])/c),
                angular_aperture=0. if object_x is None else float(min(limits)))


def admitted_interval(surfaces, object_x, height):
    pre, _ = matrices(surfaces)
    low, high = -math.inf, math.inf
    for s, p in zip(surfaces, pre):
        a, b = (p @ translation(-object_x))[0]
        if abs(b) < EPS:
            if abs(a*height) > s.aperture/2 + EPS:
                return None
        else:
            ends = sorted(((-s.aperture/2-a*height)/b, (s.aperture/2-a*height)/b))
            low, high = max(low, ends[0]), min(high, ends[1])
    return None if low > high + EPS else (low, high)


def trace(surfaces, object_x, height, angle, end_x):
    state = np.array([height, angle], dtype=float)
    x, n = object_x, 1.
    xs, ys = [x], [height]
    max_angle = abs(angle)
    for s in surfaces:
        state = translation(s.x-x, n) @ state
        xs.append(s.x); ys.append(float(state[0]))
        if abs(state[0]) > s.aperture/2 + 1e-8:
            return dict(x=xs, y=ys, blocked=s.name, max_angle=max_angle)
        state = s.matrix @ state
        x, n = s.x, s.n_after
        max_angle = max(max_angle, abs(state[1]/n))
    last_state = state.copy()
    state = translation(end_x-x, n) @ state
    xs.append(end_x); ys.append(float(state[0]))
    return dict(x=xs, y=ys, blocked=None, max_angle=max_angle, final=last_state)
