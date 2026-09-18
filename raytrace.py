"""Non-sequential meridional ray tracing on the actual spherical surfaces."""
from dataclasses import dataclass, replace
import math
import numpy as np
from optics import Surface, build, analyze, sag, translation

TOL = 1e-7


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def reflect(direction, normal):
    d, n = unit(direction), unit(normal)
    return unit(d - 2*np.dot(d, n)*n)


def refract(direction, normal, n1, n2):
    """Returns (outgoing unit direction, total internal reflection)."""
    d, n = unit(direction), unit(normal)
    if np.dot(d, n) > 0:
        n = -n
    cos_i = -np.dot(d, n)
    ratio = n1/n2
    sin_t2 = ratio**2 * max(0., 1.-cos_i*cos_i)
    if sin_t2 > 1.:
        return reflect(d, n), True
    return unit(ratio*d+(ratio*cos_i-math.sqrt(max(0., 1.-sin_t2)))*n), False


@dataclass
class Boundary:
    x: float
    radius: float
    aperture: float
    name: str
    kind: str = 'refraction'
    n_left: float = 1.
    n_right: float = 1.

    def intersect(self, point, direction, include_origin=False):
        minimum = -TOL if include_origin else TOL
        candidates = []
        # The mount starts at the cap edge, never at an imaginary vertex plane.
        if abs(direction[0]) > 1e-12:
            edge_x = self.x + float(sag(self.radius, self.aperture/2))
            t = (edge_x-point[0])/direction[0]
            if t > minimum:
                q = point+t*direction
                if self.kind == 'stop' or abs(q[1]) > self.aperture/2+TOL:
                    candidates.append((t, q, np.array([1., 0.]), abs(q[1]) > self.aperture/2+TOL))
                elif math.isinf(self.radius):
                    candidates.append((t, q, np.array([1., 0.]), False))
        if self.kind != 'stop' and not math.isinf(self.radius):
            center = np.array([self.x+self.radius, 0.])
            # Work relative to the vertex, avoiding subtraction of R² terms.
            delta = point-np.array([self.x, 0.])
            b = float(np.dot(delta, direction)-self.radius*direction[0])
            c = float(delta[0]*(delta[0]-2*self.radius)+delta[1]**2)
            disc = b*b-c
            if disc >= 0:
                root = math.sqrt(disc)
                stable_root = -b-math.copysign(root, b)
                roots = [stable_root, c/stable_root] if stable_root != 0 else [-b]
                for t in roots:
                    if t <= minimum:
                        continue
                    q = point+t*direction
                    # Reject the opposite hemisphere: only the selected cap exists.
                    if abs(q[1]) <= self.aperture/2+TOL and (q[0]-center[0])*self.radius <= TOL:
                        normal = unit(q-center)
                        if normal[0] < 0:
                            normal = -normal
                        candidates.append((t, q, normal, False))
        return min(candidates, key=lambda c: c[0]) if candidates else None


@dataclass
class Rim:
    x1: float
    x2: float
    y: float
    name: str
    kind: str = 'rim'

    def intersect(self, point, direction):
        if abs(direction[1]) < 1e-12:
            return None
        t = (self.y-point[1])/direction[1]
        q = point+t*direction
        if t > TOL and self.x1+TOL < q[0] < self.x2-TOL:
            return t, q, np.array([0., 1.]), True
        return None


def geometry(elements, diameter, wavelength):
    build(elements, diameter, wavelength)  # Validate common optical parameters.
    boundaries = [Boundary(0, math.inf, diameter, 'Abertura inicial', 'stop')]
    last_extent = 0.
    for original in sorted(elements, key=lambda e: e.position):
        e = replace(original, aperture=original.clear_aperture)
        if e.lens:
            r1, r2 = e.radii()
            n = e.n(wavelength)
            edge1 = e.position+float(sag(r1, e.aperture/2))
            edge2 = e.position+e.thickness+float(sag(r2, e.aperture/2))
            extent1 = min(e.position, edge1)
            extent2 = max(e.position+e.thickness, edge2)
            boundaries.extend([Boundary(e.position, r1, e.aperture, e.name+' · cara 1', n_left=1., n_right=n),
                               Boundary(e.position+e.thickness, r2, e.aperture, e.name+' · cara 2', n_left=n, n_right=1.)])
            boundaries.extend(Rim(edge1, edge2, sign*e.aperture/2, e.name+' · borde') for sign in [-1, 1])
        elif e.kind == 'Diafragma':
            extent1, extent2 = e.position, e.position+e.thickness
            boundaries.append(Boundary(e.position, math.inf, e.aperture, e.name, 'stop'))
            if e.thickness > 0:
                boundaries.append(Boundary(extent2, math.inf, e.aperture, e.name+' · salida', 'stop'))
                boundaries.extend(Rim(extent1, extent2, sign*e.aperture/2, e.name+' · pared') for sign in [-1, 1])
        else:
            r = math.inf if e.kind == 'Espejo plano' else (-abs(e.r1) if e.kind == 'Espejo cóncavo' else abs(e.r1))
            edge = e.position+float(sag(r, e.aperture/2))
            extent1, extent2 = min(e.position, edge), max(e.position, edge)
            boundaries.append(Boundary(e.position, r, e.aperture, e.name, 'mirror'))
        if extent1 <= last_extent+TOL:
            raise ValueError(f'{e.name}: separa sus superficies y monturas del elemento anterior y de la abertura inicial.')
        last_extent = extent2
    return boundaries


def physical_paraxial(elements, diameter, wavelength, object_x):
    """Gaussian reference along the axial itinerary, including return through lenses."""
    forward = build(elements, diameter, wavelength)
    mirror = next((e for e in sorted(elements, key=lambda e: e.position) if e.kind.startswith('Espejo')), None)
    if mirror is None:
        path = forward
        output_x, direction = forward[-1].x, 1
    else:
        # Surface index follows the builder ordering, and all physical boundaries
        # have distinct positions (validated by geometry).
        i = next(i for i, s in enumerate(forward) if s.kind == 'mirror')
        path = forward[:i+1]
        for j in range(i-1, -1, -1):
            s = forward[j]
            n_back = forward[j-1].n_after if j else 1.
            path.append(Surface(2*mirror.position-s.x, s.aperture, s.matrix.copy(), s.name+' · retorno', n_back, s.kind))
        output_x, direction = 0., -1
    result = analyze(path, object_x)
    unfolded_end = path[-1].x
    image_distance = None if result['image_x'] is None else result['image_x']-unfolded_end
    for key in ['image_x', 'exit_x', 'h2']:
        if result[key] is not None:
            result[key] = output_x+direction*(result[key]-unfolded_end)
    active = [s.x for j, s in enumerate(path) if s.kind == 'mirror' or
              not np.allclose(s.matrix, np.eye(2)) or s.n_after != (path[j-1].n_after if j else 1.)]
    last_active = active[-1] if active else 0.
    last_active_x = last_active if mirror is None or last_active <= mirror.position else 2*mirror.position-last_active
    image_real = image_distance is not None and image_distance + unfolded_end-last_active >= 0
    result.update(output_x=output_x, output_direction=direction, image_distance=image_distance,
                  image_real=image_real, path=path, mirror_x=None if mirror is None else mirror.position,
                  last_active_x=last_active_x,
                  back_focus_vertex=None if result['back_focus'] is None else result['back_focus']+unfolded_end-last_active)
    return result


def trace_exact(boundaries, object_x, height, angle, xmin, xmax, max_events=100):
    point = np.array([object_x, height], dtype=float)
    direction = np.array([math.cos(angle), math.sin(angle)])
    points, events = [point.copy()], []
    n = 1.
    blocked = None
    processed = set()
    for _ in range(max_events):
        candidates = []
        for boundary in boundaries:
            hit = (boundary.intersect(point, direction, include_origin=id(boundary) not in processed)
                   if isinstance(boundary, Boundary) else boundary.intersect(point, direction))
            if hit is not None:
                candidates.append((hit[0], boundary, hit))
        if not candidates:
            break
        _, boundary, (_, q, normal, clipped) = min(candidates, key=lambda c: c[0])
        if np.linalg.norm(q-point) > TOL:
            processed.clear()
        processed.add(id(boundary))
        points.append(q.copy())
        incoming = direction.copy()
        n_before = n
        if clipped:
            blocked = boundary.name
            event = 'Bloqueo'
        elif boundary.kind == 'mirror':
            direction = reflect(direction, normal)
            event = 'Reflexión (100 %)'
        elif boundary.kind == 'refraction':
            target = boundary.n_right if np.dot(direction, normal) > 0 else boundary.n_left
            direction, tir = refract(direction, normal, n, target)
            if not tir:
                n = target
            event = 'Reflexión interna total' if tir else 'Refracción'
        else:
            event = 'Abertura'
        cos_inc = np.clip(abs(np.dot(incoming, normal)), 0., 1.)
        cos_out = np.clip(abs(np.dot(direction, normal)), 0., 1.)
        events.append(dict(surface=boundary.name, event=event, point=q.copy(), incoming=incoming,
                           outgoing=direction.copy(), normal=normal, n_before=n_before, n_after=n,
                           incidence=math.degrees(math.acos(cos_inc)), outgoing_angle=math.degrees(math.acos(cos_out))))
        point = q
        if blocked:
            break
    else:
        blocked = 'Límite de interacciones (posible rayo atrapado)'
    exit_point, exit_direction = point.copy(), direction.copy()
    if blocked is None:
        if abs(direction[0]) > 1e-10:
            target_x = xmax if direction[0] > 0 else xmin
            length = (target_x-point[0])/direction[0]
        else:
            length = xmax-xmin
        if length > 0:
            points.append(point+length*direction)
    coords = np.asarray(points)
    return dict(x=coords[:,0], y=coords[:,1], blocked=blocked, events=events,
                exit_point=exit_point, exit_direction=exit_direction)


def focal_points(elements, diameter, wavelength, object_x):
    """Isolated-element focal positions plus combined-system focal positions."""
    rows = []
    for i, element in enumerate(sorted(elements, key=lambda e: e.position), 1):
        if element.kind == 'Diafragma':
            continue
        r = physical_paraxial([element], diameter, wavelength, object_x)
        rows.append(dict(name=element.name, label=f'F{i}', label_prime=f'F{i}′',
                         focal=r['focal'], front=r['front_focus'],
                         back=None if r['back_focus'] is None else r['output_x']+r['output_direction']*r['back_focus']))
    r = physical_paraxial(elements, diameter, wavelength, object_x)
    rows.append(dict(name='Sistema completo', label='F', label_prime='F′', focal=r['focal'],
                     front=r['front_focus'], back=None if r['back_focus'] is None else r['output_x']+r['output_direction']*r['back_focus']))
    return rows


def exact_axial_aperture_scale(boundaries, object_x, height, slope, xmin, xmax):
    """Find the connected axial bundle's real limiting ray, approached inside.

    Height and slope are scaled together. The axial itinerary must remain
    unchanged; no clipping is bypassed and TIR branches are not substituted.
    Surface edges are inclusive; numerical search retains the admitted endpoint.
    """
    if abs(height)+abs(slope) < 1e-14:
        return 1.
    center = trace_exact(boundaries, object_x, 0., 0., xmin, xmax)
    itinerary = [(e['surface'], e['event']) for e in center['events']]

    def admitted(scale):
        ray = trace_exact(boundaries, object_x, height*scale, math.atan(slope*scale), xmin, xmax)
        return ray['blocked'] is None and [(e['surface'], e['event']) for e in ray['events']] == itinerary

    low, high = 0., 1.
    # Find the first rejected sample while moving outwards from the axis.
    # Dense sampling prevents jumping across a normal vignetting transition.
    for candidate in np.linspace(1/32, 1., 32):
        if not admitted(float(candidate)):
            high = float(candidate)
            break
        low = float(candidate)
    else:
        high = 1.05
        while high < 64 and admitted(high):
            low, high = high, high*1.05
    for _ in range(42):
        middle = (low+high)/2
        if admitted(middle):
            low = middle
        else:
            high = middle
    return low


def construction_rays(result, object_x, height):
    """Three cardinal construction rays, generalized to thick systems in air."""
    rays = [('Paralelo al eje', 0.)]
    focus, nodal = result['front_focus'], result['h1']
    if focus is not None and abs(focus-object_x) > 1e-10:
        rays.append(('Por F → salida paralela', -height/(focus-object_x)))
    if nodal is not None and abs(nodal-object_x) > 1e-10:
        rays.append(('Nodal H → H′', -height/(nodal-object_x)))
    return rays


def axial_source_bundle(result, source, count, launch_x):
    """Axial parallel bundle or rays with incident conjugate at front focus.

    Launch upstream of every physical boundary, including for a virtual F.
    Bounds are paraxial; exact surface clipping remains the tracer's job.
    Returns (launch x, [(height, slope), ...]).
    """
    if source == 'infinity':
        basis = np.array([1., 0.])
    elif source == 'focus':
        focus = result['front_focus']
        if focus is None:
            raise ValueError('El sistema es afocal: no hay un foco F finito desde el que emitir.')
        basis = np.array([-focus, 1.])
        if focus < 0:
            launch_x = focus
    else:
        raise ValueError('Fuente axial desconocida.')
    limits = [s.aperture/(2*abs((p @ basis)[0]))
              for s, p in zip(result['path'], result['pre']) if abs((p @ basis)[0]) > 1e-10]
    radius = min(limits)
    parameters = np.linspace(-radius, radius, count)
    return launch_x, [(float(t*(basis[0]+launch_x*basis[1])), float(t*basis[1])) for t in parameters]


def trace_gaussian(result, object_x, height, slope, xmin, xmax):
    """Paraxial transfer at tangent planes, mapped back to physical x after reflection."""
    path = result['path']
    state = np.array([height, slope], dtype=float)
    previous, n, sign = object_x, 1., 1
    mirror = result['mirror_x']
    points, events, blocked = [[object_x, height]], [], None
    for surface in path:
        state = translation(surface.x-previous, n) @ state
        x = surface.x if mirror is None or surface.x <= mirror else 2*mirror-surface.x
        q = np.array([x, state[0]])
        points.append(q.tolist())
        incoming = unit([sign, state[1]/n])
        before_n, before_u = n, state[1]/n
        if abs(state[0]) > surface.aperture/2+1e-8:
            blocked = surface.name
            event = 'Bloqueo'
        else:
            state = surface.matrix @ state
            n = surface.n_after
            if surface.kind == 'mirror':
                sign = -sign
                event = 'Reflexión paraxial'
            elif surface.kind == 'stop':
                event = 'Abertura'
            else:
                event = 'Refracción paraxial'
        direction = unit([sign, state[1]/n])
        events.append(dict(surface=surface.name, event=event, point=q, incoming=incoming,
                           outgoing=direction.copy(), n_before=before_n, n_after=n,
                           u_before=before_u, u_after=state[1]/n,
                           incidence=None, outgoing_angle=None))
        previous = surface.x
        if blocked:
            break
    exit_point = np.asarray(points[-1])
    if blocked is None:
        xend = xmax if sign > 0 else xmin
        yend = exit_point[1]+abs(xend-exit_point[0])*state[1]/n
        points.append([xend, yend])
    coords = np.asarray(points)
    return dict(x=coords[:,0], y=coords[:,1], blocked=blocked, events=events,
                exit_point=exit_point, exit_direction=direction)


def exact_admitted_interval(boundaries, object_x, height, xmin, xmax):
    """Connected transmitted angular interval, including its limiting rays.

    The launch parameter is slope (tan(angle)), for the same finite source
    throughout. Require the axial itinerary so missed faces and TIR do not
    masquerade as transmitted marginal rays.
    """
    axial = trace_exact(boundaries, object_x, 0., 0., xmin, xmax)
    itinerary = [(e['surface'], e['event']) for e in axial['events']]
    entrance = boundaries[0]
    distance = entrance.x-object_x
    if distance <= 0 or axial['blocked']:
        return None
    lo, hi = (-entrance.aperture/2-height)/distance, (entrance.aperture/2-height)/distance
    def admitted(u):
        ray = trace_exact(boundaries, object_x, height, math.atan(u), xmin, xmax)
        return ray['blocked'] is None and [(e['surface'], e['event']) for e in ray['events']] == itinerary
    # Include the ray directed toward the optical axis even for narrow lenses.
    candidates = sorted(set(np.linspace(lo, hi, 129).tolist()+[-height/(b.x-object_x) for b in boundaries if isinstance(b, Boundary) and b.x > object_x]))
    seeds = [u for u in candidates if lo <= u <= hi and admitted(u)]
    if not seeds:
        return None
    center = min(seeds, key=lambda u: abs(u-(lo+hi)/2))
    ends = []
    for edge in (lo, hi):
        inside = center
        outside = edge
        for candidate in np.linspace(center, edge, 65)[1:]:
            if not admitted(float(candidate)):
                outside = float(candidate)
                break
            inside = float(candidate)
        else:
            ends.append(edge)
            continue
        for _ in range(48):
            mid = (inside+outside)/2
            if admitted(mid):
                inside = mid
            else:
                outside = mid
        ends.append(inside)
    return tuple(ends)


def exact_chief_slope(boundaries, result, object_x, height, interval, xmin, xmax):
    """Shoot toward the actual stop centre along the transmitted itinerary."""
    if interval is None:
        return None
    name = result['path'][result['stop']].name
    returning = name.endswith(' · retorno')
    name = name.removesuffix(' · retorno')
    def residual(u):
        ray = trace_exact(boundaries, object_x, height, math.atan(u), xmin, xmax)
        hits = [e for e in ray['events'] if e['surface'] == name]
        return hits[-1 if returning else 0]['point'][1] if hits else None
    lo, hi = interval
    left, right = residual(lo), residual(hi)
    if left is None or right is None or left*right > 0:
        return None
    for _ in range(48):
        mid = (lo+hi)/2
        value = residual(mid)
        if abs(value) < 1e-12:
            return mid
        if left*value <= 0:
            hi = mid
        else:
            lo, left = mid, value
    return (lo+hi)/2


def ray_image(rays):
    """Least transverse spread of outgoing lines; None for parallel rays.

    Return x, mean height and RMS spot radius. With two rays this is their
    actual crossing (or virtual crossing); with aberration it is a best plane.
    """
    lines = [(r['exit_direction'][1]/r['exit_direction'][0], r['exit_point'])
             for r in rays if r['blocked'] is None and abs(r['exit_direction'][0]) > 1e-12]
    if len(lines) < 2:
        return None
    slopes = np.array([u for u, q in lines])
    intercepts = np.array([q[1]-u*q[0] for u, q in lines])
    centered = slopes-slopes.mean()
    variance = float(centered@centered)
    if variance < 1e-20:
        return None
    x = -float(centered@(intercepts-intercepts.mean()))/variance
    heights = slopes*x+intercepts
    return float(x), float(heights.mean()), float(heights.std())


def exact_back_focus(elements, diameter, wavelength, count=5):
    """Best focus of a parallel axial bundle with the same real aperture rule."""
    result = physical_paraxial(elements, diameter, wavelength, None)
    boundaries = geometry(elements, diameter, wavelength)
    end = max([0.]+[e.position+e.thickness for e in elements])+200.
    x, rays = axial_source_bundle(result, 'infinity', count, -100.)
    h, u = rays[-1]
    scale = exact_axial_aperture_scale(boundaries, x, h, u, -300., end)
    traced = [trace_exact(boundaries, x, y*scale, math.atan(slope*scale), -300., end) for y, slope in rays]
    return ray_image(traced)
