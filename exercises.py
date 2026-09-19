"""Exercise generation and server-side assessment, independent of the UI."""
from dataclasses import asdict, replace
import math
import random
import numpy as np
from optics import Element, sag, admitted_interval
from presets import PRESETS
from raytrace import geometry, physical_paraxial, construction_rays, trace_exact, exact_axial_aperture_scale, exact_admitted_interval

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
        interval = exact_admitted_interval(geometry(elements, 100, 550), object_x, height, xmin, xmax)
        if interval is None:
            raise ValueError('No transmitted bundle from the object tip.')
        candidates=[('Principal (chief) · centro del stop',height,chief_slope),
                    ('Marginal superior · borde útil',height,interval[1]),
                    ('Marginal inferior · borde útil',height,interval[0])]
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
        return dict(id=f'{seed}-{count}-{mode}-tip-v2', revision='tip-v2', seed=seed, mode=mode, stop=result.get('exercise_stop'), elements=[asdict(e) for e in elements],
                    object_x=obj, object_height=height, rays=rays, xmin=xmin, xmax=xmax,
                    front_focus=result['front_focus'], principal=result['h1'],
                    position_tolerance=POSITION_TOL, point_tolerance=POINT_TOL, angle_tolerance=ANGLE_TOL)
    raise ValueError('No se ha encontrado un montaje adecuado; genera otro ejercicio.')


def public_exercise(exercise):
    """Only placement geometry and ray labels go to the canvas, never solution references."""
    result = {k: v for k, v in exercise.items() if k not in ('rays', 'stop', 'front_focus', 'principal')}
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
    """Explain the first actionable error per ray, avoiding downstream cascades."""
    issues, passed, markers = [], [], []
    scene = scene if isinstance(scene, dict) else {}
    placed = scene.get('placements', {})
    placed = placed if isinstance(placed, dict) else {}
    for key, target in [('object', exercise['object_x'])]+[(e['name'], e['position']) for e in exercise['elements']]:
        name = 'el objeto O' if key == 'object' else f'el elemento {key}'
        point = _point(placed.get(key))
        if point is None:
            issues.append(f'Falta colocar {name}. Selecciona su herramienta y haz clic sobre el eje óptico en x = {target:g} mm, y = 0 mm. Después podrás empezar a trazar los rayos.')
        elif abs(point[0]-target) > POSITION_TOL or abs(point[1]) > POSITION_TOL:
            issues.append(f'Has colocado {name} en una posición incorrecta: x = {point[0]:.2f} mm, y = {point[1]:.2f} mm. Según el enunciado debe estar en x = {target:g} mm, y = 0 mm. Vuelve a seleccionar su herramienta y colócalo allí; al moverlo se borrarán los rayos para que puedas trazarlos sobre el montaje corregido.')
        else:
            passed.append(f'La posición de {name} coincide con el enunciado, dentro del margen de {POSITION_TOL:g} mm.')
    if issues:
        return dict(correct=False, issues=issues, passed=passed, markers=markers)

    student_rays = scene.get('rays', [])
    student_rays = student_rays if isinstance(student_rays, list) else []
    def heading(vector):
        return math.degrees(math.atan2(vector[1], vector[0]))

    for expected in exercise['rays']:
        matches = [r for r in student_rays if isinstance(r, dict) and r.get('id') == expected['id']]
        prefix = expected['label']
        intro = f'**{prefix}.** '
        if not matches:
            issues.append(intro+'Todavía no has terminado este rayo. Selecciónalo en «Herramienta», marca su origen y un punto en cada superficie que atraviese o en la que se refleje. Añade un punto después de la última interacción y pulsa «Terminar rayo» o haz doble clic.')
            continue
        submitted = matches[-1].get('points', [])
        if not isinstance(submitted, list) or len(submitted) > 100:
            issues.append(intro+'No se puede leer el trazado guardado. Selecciona este rayo, pulsa «Borrar rayo seleccionado» y dibújalo de nuevo marcando únicamente el origen, las interacciones y el extremo final.')
            continue
        pts = [_point(p) for p in submitted]
        target = np.asarray(expected['points'])
        if len(pts) < 2 or any(p is None for p in pts):
            issues.append(intro+'El trazado no contiene puntos suficientes o alguna coordenada no es válida. Bórralo y marca, por este orden, el origen en O, cada encuentro con una superficie y un punto final de salida.')
            continue
        if np.linalg.norm(pts[0]-target[0]) > POINT_TOL:
            origin = 'el punto donde O toca el eje óptico' if abs(target[0,1]) < 1e-9 else 'el extremo superior del objeto O'
            issues.append(intro+f'El primer punto está en ({pts[0][0]:.2f}, {pts[0][1]:.2f}) mm, pero este rayo debe salir de {origin}, en x = {target[0,0]:g} mm, y = {target[0,1]:g} mm. Vuelve a dibujarlo desde ese punto antes de ajustar su dirección.')
            continue
        if len(pts) != len(target):
            route = ' → '.join(expected['surfaces'])
            issues.append(intro+f'Has marcado {len(pts)-2} puntos intermedios y este recorrido necesita {len(target)-2}. Coloca un punto en cada superficie, en este orden: {route}. Una lente tiene dos caras; si el rayo vuelve tras un espejo, hay que marcar también las caras del regreso. El origen y el extremo final se cuentan aparte. No añadas puntos intermedios en tramos rectos.')
            continue
        initial_error = angle_error(pts[1]-pts[0], target[1]-target[0])
        if initial_error > ANGLE_TOL:
            goal = ('el centro de la superficie limitante indicada en el enunciado' if 'chief' in prefix
                    else 'el borde útil superior del haz' if 'superior' in prefix
                    else 'el borde útil inferior del haz' if 'inferior' in prefix
                    else 'la referencia indicada por el tipo de rayo')
            issues.append(intro+f'El tramo que sale de O apunta en una dirección que no corresponde a este rayo: debe dirigirse hacia {goal}, teniendo en cuenta las refracciones previas. Su ángulo inicial es {heading(pts[1]-pts[0]):.2f}° y el esperado es {heading(target[1]-target[0]):.2f}°, medidos desde +x en coordenadas físicas. Recoloca el primer encuentro con {expected["surfaces"][0]}, cerca de x = {target[1,0]:.2f} mm, y = {target[1,1]:.2f} mm. La diferencia admitida es {ANGLE_TOL:g}°. Revisa este tramo antes de los siguientes.')
            continue
        count_before = len(issues)
        for i, surface in enumerate(expected['surfaces'], 1):
            if np.linalg.norm(pts[i]-target[i]) > POINT_TOL:
                issues.append(intro+f'En la interacción {i}, con {surface}, has marcado ({pts[i][0]:.2f}, {pts[i][1]:.2f}) mm. El rayo debe alcanzar esa superficie cerca de x = {target[i,0]:.2f} mm, y = {target[i,1]:.2f} mm. Sitúa el cambio de dirección sobre la curva, usando «Ajustar a la superficie». Se admite una distancia de {POINT_TOL:g} mm al punto esperado. Corrige este encuentro antes de continuar con el resto del recorrido.')
                break
            outgoing = pts[i+1]-pts[i]
            direction = np.asarray(expected['directions'][i-1])
            error = angle_error(outgoing, direction)
            if error > ANGLE_TOL:
                mirror = any(e['kind'].startswith('Espejo') for e in exercise['elements'] if surface.startswith(e['name']+' ·') or surface == e['name'])
                law = ('En la reflexión, el rayo vuelve al medio del que venía y el ángulo de salida debe ser igual al de entrada, ambos medidos respecto de la normal.' if mirror else
                       'Aplica la ley de Snell, n₁·sen(i) = n₂·sen(r). La normal es la recta perpendicular a la superficie en ese punto; en una cara esférica apunta al centro de curvatura. Al pasar a un índice mayor el rayo se acerca a la normal, y al pasar a uno menor se aleja.')
                issues.append(intro+f'El segmento que sale de {surface}, después de la interacción {i}, tiene una dirección incorrecta. '+law+f' Tu segmento forma {heading(outgoing):.2f}° respecto de +x y debería formar aproximadamente {heading(direction):.2f}°. La diferencia es {error:.2f}° y se admiten {ANGLE_TOL:g}°. Conserva el punto de esta interacción y corrige el siguiente punto para orientar el segmento. Estos ángulos usan las distancias físicas: no los midas directamente en pantalla, porque la escala vertical está ampliada.')
                break
        if len(issues) == count_before and np.linalg.norm(pts[-1]-pts[-2]) < 10:
            issues.append(intro+'El rayo termina demasiado cerca de la última superficie. Continúa por la misma recta de salida durante al menos 10 mm y termina allí con doble clic o «Terminar rayo». Esa distancia permite comprobar su dirección; no debes pararlo en el borde del elemento.')
        if len(issues) == count_before:
            passed.append(f'{prefix}: el origen, los encuentros con todas las superficies y las direcciones de salida son correctos dentro de las tolerancias. También has prolongado el tramo final lo suficiente.')
    if scene.get('draft'):
        issues.append('Queda un rayo en edición que todavía no has terminado. Si quieres entregarlo, añade su punto final y pulsa «Terminar rayo»; si era un intento que no quieres conservar, pulsa Escape. Después vuelve a entregar el ejercicio.')
    return dict(correct=not issues, issues=issues, passed=passed, markers=markers)
