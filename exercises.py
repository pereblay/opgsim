"""Exercise generation and server-side assessment, independent of the UI."""
from dataclasses import asdict, replace
import math
import random
import numpy as np
from optics import Element, sag, admitted_interval
from presets import PRESETS
from raytrace import geometry, physical_paraxial, construction_rays, trace_exact, exact_axial_aperture_scale

POSITION_TOL = 2.0  # mm, generous enough for clicks; shown to students
POINT_TOL = 2.0
ANGLE_TOL = 2.0  # degrees in physical coordinates


def reference_rays(elements, object_x, height, xmin, xmax, mode='construction'):
    result = physical_paraxial(elements, 100, 550, object_x)
    candidates = construction_rays(result, object_x, height)
    if len(candidates) < 2:
        candidates.append(('Hacia el vértice del espejo', -height/(elements[0].position-object_x)))
    # No entrance aperture or diaphragm is part of the exercise.
    boundaries = geometry(elements, 100, 550)[1:]
    candidates = [(label, height, slope) for label, slope in candidates]
    if mode == 'chief_marginal':
        slope = admitted_interval(result['path'], object_x, 0.)[1]
        slope *= exact_axial_aperture_scale(boundaries, object_x, 0., slope, xmin, xmax)
        # Identify the actual limiting face on the exact marginal's itinerary.
        edge = trace_exact(boundaries, object_x, 0., math.atan(slope), xmin, xmax)
        faces = {b.name:b for b in boundaries if hasattr(b,'aperture')}
        hits = [e for e in edge['events'] if e['event'] in ('Refracción','Reflexión (100 %)')]
        limiting = max(range(len(hits)),key=lambda i: abs(hits[i]['point'][1])/(faces[hits[i]['surface']].aperture/2))
        target_name = hits[limiting]['surface']
        occurrence = sum(e['surface']==target_name for e in hits[:limiting])
        result['exercise_stop'] = dict(name=target_name+(' · retorno' if occurrence else ''), x=faces[target_name].x)
        # Numerically aim the field chief through the centre of that real face.
        chief_slope = -height/(faces[target_name].x-object_x)
        def chief_height(u):
            ray=trace_exact(boundaries,object_x,height,math.atan(u),xmin,xmax)
            matches=[e for e in ray['events'] if e['surface']==target_name and e['event'] in ('Refracción','Reflexión (100 %)')]
            if len(matches)<=occurrence:
                raise ValueError('Chief cannot reach the limiting face.')
            return float(matches[occurrence]['point'][1])
        for _ in range(12):
            y=chief_height(chief_slope)
            if abs(y)<1e-8:
                break
            derivative=(chief_height(chief_slope+1e-6)-chief_height(chief_slope-1e-6))/2e-6
            if abs(derivative)<1e-8:
                raise ValueError('Singular chief aiming.')
            chief_slope-=y/derivative
        if abs(chief_height(chief_slope))>1e-6:
            raise ValueError('Chief aiming did not converge.')
        candidates=[('Principal (chief) · centro del stop',height,chief_slope),
                    ('Marginal superior · borde útil',0.,slope),
                    ('Marginal inferior · borde útil',0.,-slope)]
    rays = []
    for i, (label, ray_height, slope) in enumerate(candidates):
        ray = trace_exact(boundaries, object_x, ray_height, math.atan(slope), xmin, xmax)
        events = [event for event in ray['events'] if event['event'] in ('Refracción', 'Reflexión (100 %)')]
        if ray['blocked'] or any(event['event'] == 'Reflexión interna total' for event in ray['events']):
            raise ValueError('The construction ray is blocked or changes the intended itinerary.')
        expected_count = 2*sum(e.lens for e in elements)
        if any(e.kind.startswith('Espejo') for e in elements):
            expected_count = 2*expected_count+1
        if len(events) != expected_count or abs(slope) > .25:
            raise ValueError('Unsuitable ray itinerary for a beginner exercise.')
        if label.startswith('Por F'):
            label = 'Dirigido hacia F (referencia paraxial)'
        elif label.startswith('Nodal'):
            label = 'Dirigido hacia H (referencia paraxial)'
        points = [[object_x, ray_height]] + [event['point'].tolist() for event in events]
        points.append([float(ray['x'][-1]), float(ray['y'][-1])])
        rays.append(dict(id=f'ray{i}', label=label, slope=float(slope), points=points,
                         surfaces=[e['surface'] for e in events],
                         directions=[e['outgoing'].tolist() for e in events]))
    return rays, result


def generate_exercise(count, seed, mode='chief_marginal'):
    if count not in (1, 2, 3):
        raise ValueError('El número de elementos debe estar entre 1 y 3.')
    if mode not in ('chief_marginal','construction'):
        raise ValueError('Modalidad de ejercicio desconocida.')
    rng = random.Random(seed)
    catalogue = {e.kind: e for group in PRESETS.values() for e in group if e.kind != 'Diafragma'}
    lenses = [e for e in catalogue.values() if e.lens]
    mirrors = [e for e in catalogue.values() if e.kind.startswith('Espejo')]
    for _ in range(300):
        has_mirror = rng.random() < .45
        chosen = [rng.choice(lenses) for _ in range(count-int(has_mirror))]
        if has_mirror:
            chosen.append(rng.choice(mirrors))
        elements = []
        for i, template in enumerate(chosen):
            element = replace(template, name=f'E{i+1}', position=float(30+85*i+rng.randrange(0, 3)*5),
                              aperture=float(rng.randrange(32, 45, 2)), thickness=float(rng.randrange(5, 9)) if template.lens else 0.,
                              r1=float(rng.randrange(90, 171, 10)), r2=-float(rng.randrange(90, 171, 10)))
            elements.append(element)
        obj, height = float(-rng.randrange(80, 151, 10)), float(rng.choice([3, 4, 5]))
        xmin, xmax = -220., float(elements[-1].position+180)
        try:
            rays, result = reference_rays(elements, obj, height, xmin, xmax, mode)
        except ValueError:
            continue
        return dict(id=f'{seed}-{count}-{mode}', seed=seed, mode=mode, stop=result.get('exercise_stop'), elements=[asdict(e) for e in elements],
                    object_x=obj, object_height=height, rays=rays, xmin=xmin, xmax=xmax,
                    front_focus=result['front_focus'], principal=result['h1'],
                    position_tolerance=POSITION_TOL, point_tolerance=POINT_TOL, angle_tolerance=ANGLE_TOL)
    raise ValueError('No se ha encontrado un montaje adecuado; genera otro ejercicio.')


def public_exercise(exercise):
    """Only hints and geometry go to the canvas, never the solution polylines."""
    result = {k: v for k, v in exercise.items() if k != 'rays'}
    result['rays'] = [dict(id=r['id'], label=r['label']) for r in exercise['rays']]
    result['shapes'] = []
    for row in exercise['elements']:
        e = Element(**row)
        ys = np.linspace(-e.aperture/2, e.aperture/2, 151)
        if e.lens:
            r1, r2 = e.radii()
            points = np.column_stack((sag(r1, ys), ys)).tolist()
            points += np.column_stack((e.thickness+sag(r2, ys[::-1]), ys[::-1])).tolist()
            points.append(points[0])
        else:
            radius = math.inf if e.kind == 'Espejo plano' else -abs(e.r1)
            points = np.column_stack((sag(radius, ys), ys)).tolist()
        result['shapes'].append(points)
    return result


def _point(value):
    try:
        a = np.asarray(value, dtype=float)
        return a if a.shape == (2,) and np.all(np.isfinite(a)) and np.max(abs(a)) < 1e6 else None
    except (TypeError, ValueError):
        return None


def angle_error(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if min(na, nb) < 1e-8:
        return 180.
    return math.degrees(math.acos(float(np.clip(np.dot(a, b)/(na*nb), -1, 1))))


def assess_exercise(exercise, scene):
    """Assess positions and every bend with exact Snell/reflection, not browser data."""
    issues, passed, markers = [], [], []
    scene = scene if isinstance(scene, dict) else {}
    placed = scene.get('placements', {})
    placed = placed if isinstance(placed, dict) else {}
    for key, target in [('object', exercise['object_x'])]+[(e['name'], e['position']) for e in exercise['elements']]:
        point = _point(placed.get(key))
        if point is None:
            issues.append(f'Coloca {"el objeto O" if key == "object" else key} sobre el eje en x={target:g} mm.')
        elif abs(point[0]-target) > POSITION_TOL or abs(point[1]) > POSITION_TOL:
            issues.append(f'{key}: posición incorrecta; sitúalo en x={target:g} mm, y=0 mm.')
            markers.append(dict(point=point.tolist(), label=key))
        else:
            passed.append(f'{key}: posición correcta.')
    # Placement errors must be resolved before interpreting the student's geometry.
    placement_ok = not issues
    student_rays = scene.get('rays', [])
    student_rays = student_rays if isinstance(student_rays, list) else []
    for expected in exercise['rays']:
        matches = [r for r in student_rays if isinstance(r, dict) and r.get('id') == expected['id']]
        prefix = expected['label']
        if not matches:
            issues.append(f'{prefix}: falta el trazado. Termínalo con doble clic.')
            continue
        if not placement_ok:
            continue
        submitted = matches[-1].get('points', [])
        if not isinstance(submitted, list) or len(submitted) > 100:
            issues.append(f'{prefix}: trazado no válido.')
            continue
        pts = [_point(p) for p in submitted]
        target = np.asarray(expected['points'])
        if len(pts) < 2 or any(p is None for p in pts):
            issues.append(f'{prefix}: marca el inicio, las interacciones y el final.')
            continue
        count_before = len(issues)
        if np.linalg.norm(pts[0]-target[0]) > POINT_TOL:
            issues.append(f'{prefix}: comienza en el punto del objeto O ({target[0,0]:g}, {target[0,1]:g}) mm; el marginal sale del eje y el chief del extremo.')
        if len(pts) != len(target):
            issues.append(f'{prefix}: se esperan {len(target)-2} puntos de interacción, uno por cara alcanzada (también en el retorno), además del inicio y del final. Has marcado {len(pts)-2}.')
            continue
        if angle_error(pts[1]-pts[0], target[1]-target[0]) > ANGLE_TOL:
            issues.append(f'{prefix}: corrige la dirección inicial; no corresponde al tipo de rayo elegido.')
        for i, surface in enumerate(expected['surfaces'], 1):
            if np.linalg.norm(pts[i]-target[i]) > POINT_TOL:
                issues.append(f'{prefix}, {surface}: el cambio de dirección debe estar cerca de x={target[i,0]:.2f}, y={target[i,1]:.2f} mm, en la superficie.')
                markers.append(dict(point=pts[i].tolist(), label=surface))
            incoming_error = angle_error(pts[i]-pts[i-1], target[i]-target[i-1])
            outgoing = pts[i+1]-pts[i]
            outgoing_error = angle_error(outgoing, np.asarray(expected['directions'][i-1]))
            if outgoing_error > ANGLE_TOL:
                law = 'la reflexión: el rayo debe regresar con ángulo igual al incidente respecto de la normal' if 'Espejo' in next((e['kind'] for e in exercise['elements'] if surface.startswith(e['name'])), '') else 'Snell: mide los ángulos respecto de la normal local'
                issues.append(f'{prefix}, {surface}: revisa {law}. Error angular de salida: {outgoing_error:.1f}°.')
            if incoming_error > ANGLE_TOL and outgoing_error <= ANGLE_TOL:
                issues.append(f'{prefix}, {surface}: el segmento incidente no sigue la trayectoria esperada.')
        if np.linalg.norm(pts[-1]-pts[-2]) < 10:
            issues.append(f'{prefix}: prolonga al menos 10 mm el último segmento antes del doble clic.')
        if len(issues) == count_before:
            passed.append(f'{prefix}: trazado correcto dentro de las tolerancias.')
    if scene.get('draft'):
        issues.append('Tienes un rayo sin terminar. Usa doble clic o cancélalo antes de entregar.')
    return dict(correct=not issues, issues=issues, passed=passed, markers=markers)
