import json
import hashlib
import importlib
import sys
from pathlib import Path
import math
from dataclasses import asdict
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from presets import PRESETS
from optics import Element, TYPES, sag, admitted_interval, EPS, build, matrix_walkthrough
from raytrace import geometry, physical_paraxial, trace_exact, focal_points, trace_gaussian, axial_source_bundle, exact_axial_aperture_scale, exact_admitted_interval, exact_chief_slope, ray_image, exact_back_focus

st.set_page_config(page_title='Banco óptico · OPGSim', page_icon='🔬', layout='wide')
# Cloud can rerun the entrypoint while keeping imported modules in memory.
# Refresh the portal and its assessment code when any of their sources change.
portal_revision = hashlib.sha256(b''.join(Path(__file__).with_name(name).read_bytes()
    for name in ('exercise_portal.py', 'exercise_canvas.js', 'exercises.py'))).hexdigest()
portal_module = sys.modules.get('exercise_portal')
if portal_module is not None and getattr(portal_module, '_loaded_revision', None) != portal_revision:
    if 'exercises' in sys.modules:
        importlib.reload(sys.modules['exercises'])
    importlib.reload(portal_module)
from exercise_portal import render_exercise_portal
sys.modules['exercise_portal']._loaded_revision = portal_revision
if st.session_state.get('portal') == 'exercises':
    render_exercise_portal()
    st.stop()
st.title('Banco óptico')
if st.button('Abrir portal de ejercicios', key='open_exercises'):
    st.session_state.portal = 'exercises'
    st.rerun()
st.caption('OPGSim · Trazado paraxial o exacto · Parámetros gaussianos · Distancias en mm · Sistema centrado en aire')

if 'elements' not in st.session_state:
    st.session_state.elements = [asdict(e) for e in PRESETS['Lente convergente']]
    st.session_state.version = 0

with st.sidebar:
    st.header('Objeto y abertura inicial')
    origin = st.number_input('Posición absoluta de referencia (mm)', value=0., step=10., help='Traslada las coordenadas del dibujo; las posiciones de los elementos son relativas a esta referencia.')
    source_mode = st.radio('Origen de los rayos', ['Objeto finito', 'Paralelos desde infinito', 'Desde el foco F'])
    finite_source = source_mode == 'Objeto finito'
    obj = st.number_input('Distancia del objeto a la referencia (mm)', max_value=-0.01, value=-120., step=10., disabled=not finite_source)
    height = st.number_input('Altura total del objeto (mm)', min_value=0., value=0., step=1., disabled=not finite_source)
    placement = st.radio('Situación del objeto', ['Por encima del eje', 'Centrado simétricamente'], disabled=not finite_source)
    diameter = st.number_input('Diámetro de abertura inicial (mm)', min_value=0.01, value=25., step=1.)
    wavelength = st.slider('Longitud de onda (nm)', 380, 780, 550)
    st.caption('La abertura inicial es física. Solo coincide con la pupila de entrada si es la abertura limitante del sistema.')
    st.header('Trazado')
    tracing_mode = st.selectbox('Modelo de rayos', ['Paraxial · aproximación matricial', 'Exacto · Snell y reflexión'], index=1)
    exact = tracing_mode.startswith('Exacto')
    ray_families = st.multiselect('Rayos que se dibujan', ['Principal y marginales', 'Haz'], default=['Principal y marginales'], disabled=not finite_source)
    st.header('Visualización')
    ray_count = st.slider('Rayos del haz por punto', 3, 15, 5, step=2)
    extension = st.number_input('Extensión visible del recorrido (mm)', min_value=1., value=160., step=20.)
    show_virtual = st.checkbox('Prolongaciones hacia imagen virtual', True)
    equal_scale = st.checkbox('Misma escala horizontal y vertical', True)
    st.header('Ejemplos')
    preset = st.selectbox('Configuración', list(PRESETS))
    if st.button('Cargar ejemplo', width="stretch"):
        st.session_state.elements = [asdict(e) for e in PRESETS[preset]]
        st.session_state.version += 1
        st.rerun()

st.subheader('1 · Elementos del sistema')
st.caption('Añade los elementos uno a uno y edita sus valores en la tabla. Se ordenan por posición. Altura = diámetro útil, centrado en el eje.')
with st.form('add', clear_on_submit=False):
    c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment='bottom')
    kind = c1.selectbox('Tipo de elemento', TYPES)
    position = c2.number_input('Distancia a la referencia (mm)', min_value=0., value=80., step=10.)
    submitted = c3.form_submit_button('Añadir elemento', width="stretch")
    if submitted:
        st.session_state.elements.append(asdict(Element(name=f'E{len(st.session_state.elements)+1}', kind=kind, position=position)))
        st.session_state.version += 1

columns = {
    'name': st.column_config.TextColumn('Nombre', required=True),
    'kind': st.column_config.SelectboxColumn('Tipo', options=TYPES, required=True, width='medium'),
    'position': st.column_config.NumberColumn('Distancia (mm)', min_value=0., required=True),
    'aperture': st.column_config.NumberColumn('Altura / Ø (mm)', min_value=.01, required=True),
    'thickness': st.column_config.NumberColumn('Grosor (mm)', min_value=0., required=True),
    'index': st.column_config.NumberColumn('n a 550 nm', min_value=1., required=True, format='%.4f'),
    'r1': st.column_config.NumberColumn('R₁ (mm)', required=True),
    'r2': st.column_config.NumberColumn('R₂ (mm)', required=True),
    'dispersion': st.column_config.NumberColumn('Cauchy B (µm²)', min_value=0., required=True, format='%.5f'),
}
edited = st.data_editor(st.session_state.elements, column_config=columns, num_rows='fixed', hide_index=True, width="stretch", key=f'editor_{st.session_state.version}')
# The current table is the source for subsequent additions and removals.
st.session_state.elements = edited
if edited:
    c1, c2 = st.columns([4, 1], vertical_alignment='bottom')
    remove = c1.selectbox('Eliminar elemento', range(len(edited)), format_func=lambda i: f'{i+1} · {edited[i]["name"]}')
    if c2.button('Eliminar seleccionado'):
        st.session_state.elements.pop(remove)
        st.session_state.version += 1
        st.rerun()
with st.expander('Convenciones, índices y límites del modelo'):
    st.markdown("""- **Modo paraxial:** aplica y₂ = y₁ + t·u y n₂u₂ = n₁u₁ − y·(n₂−n₁)/R en los planos de vértice. En aire, los puntos nodales coinciden con H/H′: el rayo nodal conserva su ángulo de entrada/salida, pero puede desplazarse lateralmente en una lente gruesa.
- **Modo exacto:** intersecciones con las superficies esféricas, ley vectorial de Snell y reflexión especular. Un espejo ideal refleja el 100 % del rayo. El trazado busca la siguiente superficie en la dirección real, incluso al regresar a través de lentes anteriores.
- **Índice por defecto: 1.** Si ambos medios tienen igual índice, no hay desviación; tampoco la hay en incidencia normal. Los ejemplos de lentes usan n = 1,5. La dispersión opcional sigue n(λ) = n(550 nm) + B·[1/λ² − 1/0,55²], con λ en µm.
- **Radios:** el signo es positivo si el centro de curvatura está a la derecha. Los tipos predefinidos asignan los signos; «Lente personalizada» conserva los introducidos. Todos los elementos están centrados en el eje y los espejos son perpendiculares a él en su vértice.
- **Aberturas y bordes:** las monturas son opacas fuera de la abertura útil; también se interceptan los bordes laterales de lentes y diafragmas. Las superficies deben estar separadas físicamente.
- **Resultados gaussianos:** focal, imagen, pupilas y planos principales son aproximaciones paraxiales del recorrido axial, incluido el doble paso cuando hay espejo. Los rayos exactos pueden no converger en un único punto debido a las aberraciones de las superficies esféricas.
- **Rayo principal (chief):** desde el extremo del objeto al centro del stop. **Marginales:** desde ese mismo punto a los dos bordes útiles del haz; también se dibuja la familia axial. Cada punto del objeto emite su principal y los dos límites de su haz. En modo exacto se buscan sobre las superficies reales; O′ indica el plano de menor dispersión del haz y O′G la referencia gaussiana. Un aspa indica un bloqueo; las prolongaciones virtuales no transportan luz.
- Se incluye reflexión interna total; no se dividen rayos por reflexión parcial de Fresnel ni se modela difracción. El objeto se considera una fuente sin pantalla opaca.
""")

try:
    elements = [Element(**row) for row in edited]
    boundaries = geometry(elements, diameter, wavelength)
    result = physical_paraxial(elements, diameter, wavelength, obj)
    if source_mode == 'Paralelos desde infinito':
        result = physical_paraxial(elements, diameter, wavelength, None)
    elif source_mode == 'Desde el foco F':
        if result['front_focus'] is None:
            st.info('El sistema es afocal: no hay un foco F finito. Selecciona rayos paralelos desde infinito o añade potencia óptica.')
            st.stop()
        result = physical_paraxial(elements, diameter, wavelength, result['front_focus'])
    surfaces = result['path']
    for element in elements:
        if element.clear_aperture < element.aperture-1e-8:
            st.info(f'{element.name}: altura útil corregida de {element.aperture:g} a {element.clear_aperture:.6g} mm por el cruce o el límite de sus superficies.')
    foci = focal_points(elements, diameter, wavelength, obj)
    if exact:
        optical_elements = [e for e in sorted(elements, key=lambda e: e.position) if e.kind != 'Diafragma']
        for focus, subsystem in zip(foci, [[e] for e in optical_elements]+[elements]):
            focus['exact_back'] = exact_back_focus(subsystem, diameter, wavelength, ray_count)
except (ValueError, TypeError, KeyError, ZeroDivisionError) as error:
    st.error(f'Revisa la configuración: {error}')
    st.stop()

bottom, top = (0., height) if placement == 'Por encima del eje' else (-height/2, height/2)
end = max([0.]+[e.position+e.thickness if e.lens or e.kind == 'Diafragma' else e.position for e in elements]) + extension
start_x = obj - extension*.25
source_rays = None
if not finite_source:
    obj, source_rays = axial_source_bundle(result, 'infinity' if source_mode == 'Paralelos desde infinito' else 'focus', ray_count, -extension*.5)
    bottom = top = 0.
    start_x = obj-extension*.25
    if exact:
        edge_height, edge_slope = source_rays[-1]
        edge_scale = exact_axial_aperture_scale(boundaries, obj, edge_height, edge_slope, start_x, end)
        source_rays = [(y*edge_scale, u*edge_scale) for y, u in source_rays]
    if source_mode == 'Desde el foco F':
        st.info('F es el foco anterior del sistema completo. La salida paraxial es paralela al eje; el trazado exacto puede presentar aberración esférica.')
        if result['front_focus'] >= 0:
            st.caption('F no está antes de la abertura inicial: se representa el haz incidente dirigido hacia F, como construcción equivalente en el espacio objeto.')
    else:
        st.info('Haz axial paralelo desde infinito. Su imagen gaussiana está en F′; un sistema afocal conserva una salida paralela.')
colors = ['#2563eb', '#dc6940', '#8b5cf6']

def base_figure():
    fig = go.Figure()
    fig.add_hline(y=0, line_color='#94a3b8', line_dash='dash')
    if finite_source:
        fig.add_trace(go.Scatter(x=[obj+origin]*2, y=[bottom, top], mode='lines+markers', line=dict(color='#0f172a', width=5), name='O · Objeto real'))
        fig.add_vline(x=obj+origin, line_color='#64748b', line_width=1)
        fig.add_annotation(x=obj+origin, y=top, text='O', showarrow=False, yshift=16, font=dict(size=16, color='#0f172a'))
    elif source_mode == 'Paralelos desde infinito':
        fig.add_annotation(x=obj+origin, y=diameter/2, text='O en ∞ · haz paralelo', showarrow=False, yshift=16)
    elif result['front_focus'] < 0:
        fig.add_trace(go.Scatter(x=[obj+origin], y=[0], mode='markers', marker=dict(size=9, color='#0f172a'), name='O = F'))
        fig.add_annotation(x=obj+origin, y=0, text='O = F', showarrow=False, yshift=40)
    def aperture(x, aperture, name):
        a = aperture/2
        for sign in [-1, 1]:
            fig.add_trace(go.Scatter(x=[x+origin]*2, y=[sign*a, sign*(a+max(diameter*.12, 2))], mode='lines', line=dict(color='#475569', width=6), name=name, showlegend=False, hovertemplate=name+'<extra></extra>'))
    aperture(0, diameter, 'Abertura inicial')
    for e in sorted(elements, key=lambda e: e.position):
        y = np.linspace(-e.clear_aperture/2, e.clear_aperture/2, 1001)
        if e.lens:
            r1, r2 = e.radii()
            left, right = e.position+sag(r1, y), e.position+e.thickness+sag(r2, y)
            fig.add_trace(go.Scatter(x=np.r_[left, right[::-1], left[:1]]+origin, y=np.r_[y, y[::-1], y[:1]], fill='toself', fillcolor='rgba(14,165,233,0.18)', line=dict(color='#0284c7', width=1.5), name=e.name, hovertemplate=e.name+f'<br>n = {e.n(wavelength):.5f}<extra></extra>'))
        elif e.kind == 'Diafragma':
            aperture(e.position, e.aperture, e.name)
            if e.thickness:
                aperture(e.position+e.thickness, e.aperture, e.name)
        else:
            r = math.inf if e.kind == 'Espejo plano' else (-abs(e.r1) if e.kind == 'Espejo cóncavo' else abs(e.r1))
            fig.add_trace(go.Scatter(x=e.position+sag(r, y)+origin, y=y, mode='lines', line=dict(color='#64748b', width=5), name=e.name))
        if not exact and e.lens:
            for vx in [e.position, e.position+e.thickness]:
                fig.add_trace(go.Scatter(x=[vx+origin]*2, y=[-e.clear_aperture/2, e.clear_aperture/2], mode='lines', line=dict(color='#94a3b8', width=1), showlegend=False, hovertemplate='Plano de vértice paraxial<extra></extra>'))
        fig.add_annotation(x=e.position+origin, y=e.aperture/2+3, text=e.name, showarrow=False, font=dict(size=11))
    for i, focus in enumerate(foci):
        if exact and focus.get('exact_back') is not None:
            fx, fy, rms = focus['exact_back']
            fig.add_trace(go.Scatter(x=[fx+origin], y=[fy], mode='markers', marker=dict(symbol='cross', size=9, color='#be123c'), showlegend=False, hovertemplate=f'{focus["label_prime"]} · haz paralelo exacto · RMS={rms:.6g} mm<extra></extra>'))
            fig.add_annotation(x=fx+origin, y=fy, text=focus['label_prime'], showarrow=False, yshift=-52-14*(i%2))
        color = '#be123c' if focus['name'] == 'Sistema completo' else '#0f766e'
        for field, label in [('front', focus['label']), ('back', focus['label_prime'])]:
            if exact:
                label += 'G'
            value = focus[field]
            if value is not None:
                fig.add_trace(go.Scatter(x=[value+origin], y=[0], mode='markers', marker=dict(symbol='x', size=11 if focus['name'] == 'Sistema completo' else 8, color=color), showlegend=False, hovertemplate=f'{label} · {focus["name"]}<br>x={value:.3f} mm (relativa)<extra></extra>'))
                # Opposite sides of the axis separate F and F′ when coincident.
                fig.add_annotation(x=value+origin, y=0, text=label, showarrow=False, yshift=(20+12*(i%2))*(1 if field=='front' else -1), font=dict(size=13, color=color))
    fig.update_layout(template='plotly_white', height=350, margin=dict(l=25, r=20, t=30, b=30), xaxis_title='Posición física x (mm)', yaxis_title='Altura (mm)', legend=dict(orientation='h', y=-.25, groupclick='togglegroup'), hovermode='closest')
    fig.update_xaxes(range=[obj+origin-10, end+origin])
    if equal_scale:
        fig.update_yaxes(scaleanchor='x', scaleratio=1)
    return fig

st.subheader('2 · Disposición de los elementos')
st.plotly_chart(base_figure(), width="stretch")
st.subheader('3 · Trazado')
st.caption('Trayectorias reales en continuo; prolongaciones virtuales en discontinuo.')
fig = base_figure()
fig.update_layout(height=520)
records, interaction_records, exact_images = [], [], []
for group, h in enumerate(sorted(set([bottom, 0., top])) if finite_source else [0.]):
    if finite_source:
        p = result['pre'][result['stop']] @ np.array([[1., -obj], [0., 1.]])
        a, b = p[0]
        stop_radius = surfaces[result['stop']].aperture/2
        rays = []
        interval = (exact_admitted_interval(boundaries, obj, h, start_x, end) if exact
                    else admitted_interval(surfaces, obj, h))
        if 'Principal y marginales' in ray_families and interval:
            chief = (exact_chief_slope(boundaries, result, obj, h, interval, start_x, end) if exact
                     else (-a*h/b if abs(b) > EPS else None))
            if chief is not None:
                rays.append(('Principal · centro del stop', chief))
            rays += [('Marginal − · borde útil', interval[0]), ('Marginal + · borde útil', interval[1])]
        if interval and 'Haz' in ray_families:
            rays += [('Marginal − · borde útil' if i == 0 else 'Marginal + · borde útil' if i == ray_count-1 else 'Haz', float(slope))
                     for i, slope in enumerate(np.linspace(*interval, ray_count))]
        unique_rays = []
        for label, slope in rays:
            if not any(abs(slope-old_slope) < 1e-10 for _, old_slope in unique_rays):
                unique_rays.append((label, slope))
        rays = unique_rays
        launches = [(label, h, slope) for label, slope in rays]
    else:
        launches = [(f'Paralelo {i+1}' if source_mode == 'Paralelos desde infinito' else f'Desde F · {i+1}', y, u) for i, (y, u) in enumerate(source_rays)]
    group_rays = []
    for label, h, slope in launches:
        theta = math.atan(slope)
        ray = trace_exact(boundaries, obj, h, theta, start_x, end) if exact else trace_gaussian(result, obj, h, slope, start_x, end)
        group_rays.append(ray)
        ray_color = colors[group]
        name = f'y={h:g} · {label}'
        fig.add_trace(go.Scatter(x=ray['x']+origin, y=ray['y'], mode='lines', line=dict(color=ray_color, width=1 if label == 'Haz' else 2, dash='solid'), opacity=.30 if label == 'Haz' else .85, name=name, legendgroup=name, showlegend=label!='Haz', hovertemplate=name+'<br>x=%{x:.3f} mm<br>y=%{y:.3f} mm<extra></extra>'))
        if label != 'Haz':
            for event in ray['events']:
                if event['event'] != 'Abertura':
                    interaction_records.append({'Rayo': name, 'Superficie': event['surface'], 'Interacción': event['event'], 'x (mm)': event['point'][0], 'y (mm)': event['point'][1], 'n incidente': event['n_before'], 'n saliente': event['n_after'], 'Incidencia / normal (°)': event['incidence'], 'Salida / normal (°)': event['outgoing_angle'], 'u incidente (paraxial)': event.get('u_before'), 'u saliente (paraxial)': event.get('u_after')})
        if ray['blocked']:
            fig.add_trace(go.Scatter(x=[ray['x'][-1]+origin], y=[ray['y'][-1]], mode='markers', marker=dict(symbol='x', color=ray_color, size=8), legendgroup=name, showlegend=False, hovertemplate=f'Interceptado: {ray["blocked"]}<extra></extra>'))
        elif not exact and show_virtual and result['image_x'] is not None and not result['image_real']:
            ximage = result['image_x']
            q, d = ray['exit_point'], ray['exit_direction']
            if abs(d[0]) > EPS:
                distance = (ximage-q[0])/d[0]
                if distance < 0:
                    fig.add_trace(go.Scatter(x=[q[0]+origin, ximage+origin], y=[q[1], q[1]+distance*d[1]], mode='lines', line=dict(color=ray_color, dash='dash', width=1), opacity=.4, legendgroup=name, showlegend=False))
        reflections = sum('Reflexión' in e['event'] for e in ray['events'])
        records.append({'Origen y (mm)': h, 'Rayo': label, ('Ángulo inicial (rad)' if exact else 'Pendiente inicial u (paraxial)'): theta if exact else slope, 'Reflexiones': reflections, 'Estado': ('Sale a la derecha' if ray['exit_direction'][0] > 0 else 'Sale a la izquierda') if not ray['blocked'] else 'Interceptado: '+ray['blocked']})

    if exact:
        image = ray_image(group_rays)
        if image is not None:
            ix, iy, rms = image
            exact_images.append({'Origen y (mm)': h, 'x imagen (mm)': ix+origin, 'y imagen (mm)': iy, 'Radio RMS (mm)': rms})
            fig.add_trace(go.Scatter(x=[ix+origin], y=[iy], mode='markers', marker=dict(color=colors[group], size=10, symbol='cross'), name=f'O′ · haz y={h:g}', hovertemplate=f'O′ · mínimo RMS={rms:.6g} mm<extra></extra>'))
            fig.add_annotation(x=ix+origin, y=iy, text='O′', showarrow=False, yshift=16)
            if show_virtual:
                for ray in group_rays:
                    active = [ev for ev in ray['events'] if ev['event'] != 'Abertura']
                    q = active[-1]['point'] if active else ray['exit_point']
                    d = ray['exit_direction']
                    if ray['blocked'] is None and abs(d[0]) > EPS and (ix-q[0])/d[0] < 0:
                        fig.add_trace(go.Scatter(x=[q[0]+origin, ix+origin], y=[q[1], q[1]+(ix-q[0])*d[1]/d[0]], mode='lines', line=dict(color=colors[group], dash='dash', width=1), opacity=.4, legendgroup=f'O′ · haz y={h:g}', showlegend=False))

for key, label, color in [('entrance_x', 'Pupila entrada', '#16a34a'), ('exit_x', 'Pupila salida', '#d97706'), ('image_x', 'Imagen paraxial', '#e11d48')]:
    x = result[key]
    if x is not None:
        fig.add_vline(x=x+origin, line_dash='dash', line_color=color, annotation_text=('Plano imagen O′G' if exact else 'Plano imagen O′') if key == 'image_x' else label)
if result['image_x'] is not None:
    m = result['magnification'] if finite_source else 0.
    fig.add_trace(go.Scatter(x=[result['image_x']+origin]*2, y=[bottom*m, top*m], mode='lines+markers', line=dict(color='#e11d48', width=4, dash='dash'), name='O′G · Imagen gaussiana' if exact else 'O′ · Imagen gaussiana'))
    fig.add_annotation(x=result['image_x']+origin, y=top*m, text='O′G' if exact else 'O′', showarrow=False, yshift=16 if m >= 0 else -16, font=dict(size=16, color='#e11d48'))
for key, dkey, label in [('entrance_x', 'entrance_diameter', 'Ø entrada'), ('exit_x', 'exit_diameter', 'Ø salida')]:
    if result[key] is not None and result[dkey] is not None:
        fig.add_trace(go.Scatter(x=[result[key]+origin]*2, y=[-result[dkey]/2, result[dkey]/2], mode='lines', line=dict(dash='dash', width=3), name=label))
# Keep the default view useful even for almost-afocal systems; zoom remains available.
span = end-obj
visible = [start_x, end]+[row['x imagen (mm)']-origin for row in exact_images if obj-span < row['x imagen (mm)']-origin < end+span]+[v for f in foci for v in [f['front'], f['back']] if v is not None and obj-span < v < end+span]+[result[k] for k in ['image_x', 'entrance_x', 'exit_x'] if result[k] is not None and obj-span < result[k] < end+span]
fig.update_xaxes(range=[min(visible)+origin-10, max(visible)+origin+10])
max_height = max([diameter, height*2]+[e.aperture for e in elements])
fig.update_yaxes(range=[-max_height, max_height])
st.plotly_chart(fig, width="stretch")
if exact_images:
    st.dataframe(exact_images, hide_index=True, width='stretch')
st.caption(('O′ se calcula con los rayos exactos dibujados (mínima dispersión transversal). O′G, FG y F′G son referencias gaussianas; la aberración puede producir distintos cruces y un radio RMS no nulo.' if exact else 'Los rayos paraxiales transmitidos desde un mismo punto concurren en O′ o en su prolongación virtual.') + ' Los elementos detrás del primer espejo no se alcanzan en este montaje centrado.')
if any(e.lens and e.index == 1 and e.dispersion == 0 for e in elements):
    st.info('Hay lentes con n = 1, igual que el aire: sus superficies no desvían la luz. Cambia su índice para simular vidrio.')

st.subheader('4 · Parámetros paraxiales del recorrido físico')
def fmt(value, unit=' mm'):
    return '∞ / no finito' if value is None else f'{value:,.3f}{unit}'

c1, c2, c3, c4 = st.columns(4)
c1.metric('Focal efectiva', fmt(result['focal']))
c2.metric('Posición de imagen gaussiana¹', fmt(result['image_x']))
c3.metric('Aumento transversal', fmt(result['magnification'], ' ×') if finite_source else 'No aplicable')
c4.metric('Altura de imagen', fmt(None if result['image_x'] is None else (abs(result['magnification'])*height if finite_source else 0.)))
st.caption('O: objeto. Imagen y focos gaussianos: sufijo G en modo exacto. O′: cruce o plano de mínima dispersión del haz mostrado; F′: mínimo del haz paralelo. El subíndice i identifica un elemento aislado.')
stop_name = surfaces[result['stop']].name
st.info(f'Abertura limitante para el objeto axial: **{stop_name}**. '+('Sistema afocal (C ≈ 0).' if result['focal'] is None else ''))
rows = [
    ('Pupila de entrada · posición¹', fmt(result['entrance_x'])),
    ('Pupila de entrada · diámetro', fmt(result['entrance_diameter'])),
    ('Pupila de salida · posición¹', fmt(result['exit_x'])),
    ('Pupila de salida · diámetro', fmt(result['exit_diameter'])),
    ('Foco anterior · posición¹', fmt(result['front_focus'])),
    ('BFL desde la última superficie óptica', fmt(result['back_focus_vertex'])),
    ('Plano principal H · posición¹', fmt(result['h1'])),
    ("Plano principal H′ · posición¹", fmt(result['h2'])),
    ('Potencia equivalente', fmt(0. if result['focal'] is None else 1000/result['focal'], ' D')),
    ('Número f nominal |f|/Ø entrada', fmt(None if result['focal'] is None or result['entrance_diameter'] is None else abs(result['focal'])/result['entrance_diameter'], '')),
    ('Semiapertura angular axial paraxial', fmt(result['angular_aperture'], ' rad')),
    ('Imagen', 'En infinito' if result['image_x'] is None else ('Real' if result['image_real'] else 'Virtual')),
]
st.dataframe([{'Parámetro': k, 'Resultado': v} for k, v in rows], hide_index=True, width="stretch")
st.caption(f'Sentido de salida axial: {"izquierda (−x)" if result["output_direction"] < 0 else "derecha (+x)"}. Plano de salida: x = {result["output_x"]:g} mm.')
st.caption('¹ Posiciones relativas a la abertura inicial. En el dibujo se suma la posición absoluta de referencia. Para pupilas en infinito, su diámetro lineal no es finito. Aire a ambos lados: los planos nodales coinciden con los principales.')
st.dataframe([{'Elemento': f['name'], 'Foco objeto': f['label']+('G' if exact else ''), 'Posición F (mm)': fmt(f['front']), 'Foco imagen': f['label_prime']+('G' if exact else ''), 'Posición F′ (mm)': fmt(f['back']), 'Focal efectiva (mm)': fmt(f['focal'])} for f in foci], hide_index=True, width='stretch')
if exact:
    st.dataframe([{'Elemento': f['name'], 'Foco imagen exacto': f['label_prime'], 'Posición relativa (mm)': f['exact_back'][0], 'Radio RMS (mm)': f['exact_back'][2]} for f in foci if f.get('exact_back') is not None], hide_index=True, width='stretch')
st.caption('Espejos planos y elementos sin potencia: focos en infinito, sin marca finita en la gráfica.')
with st.expander('Rayos, ángulos de interacción y matriz ABCD'):
    for h in sorted(set([bottom, 0., top])) if finite_source else []:
        interval = admitted_interval(surfaces, obj, h)
        st.write(f'Estimación paraxial para y = {h:g} mm: '+('totalmente bloqueado.' if interval is None else f'intervalo angular admitido [{interval[0]:.5f}, {interval[1]:.5f}] rad.'))
    st.write('Matriz del recorrido axial, incluyendo retornos. Estado (y, nθ) con θ respecto al sentido de propagación:')
    st.code(np.array2string(result['matrix'], precision=6))
    st.dataframe(records, hide_index=True, width="stretch")
    st.dataframe(interaction_records, hide_index=True, width="stretch")
st.subheader('5 · Equivalente matricial del sistema')
st.markdown('La matriz ABCD transforma el vector **(altura, θ)** en la aproximación paraxial. Aquí la altura se llama **y**, para distinguirla de la coordenada longitudinal x del dibujo. θ se expresa en radianes respecto del sentido local de propagación.')
selection = st.selectbox('Recorrido matricial', range(len(elements)+1), format_func=lambda i: 'Sistema completo · incluye espacios y retorno' if i == 0 else f'Elemento aislado {i} · {elements[i-1].name}')
if selection == 0:
    matrix_path, matrix_start = surfaces, 0.
    st.caption(f'Entrada: abertura inicial x=0 mm. Salida: x={result["output_x"]:g} mm; sentido {"−x" if result["output_direction"] < 0 else "+x"}.')
else:
    selected_element = elements[selection-1]
    matrix_path = build([selected_element], diameter, wavelength)[1:]
    matrix_start = selected_element.position
    st.caption('Elemento aislado: desde justo antes de su primera superficie hasta justo después de la última interacción. No incluye los espacios exteriores ni los demás elementos.')
mi1, mi2 = st.columns(2)
input_height = mi1.number_input('Altura de entrada y (mm)', value=1., step=.1, key='matrix_height')
input_theta = mi2.number_input('Ángulo de entrada θ (rad)', value=0., step=.001, format='%.5f', key='matrix_theta')
mtotal, mout, mrows = matrix_walkthrough(matrix_path, input_height, input_theta, matrix_start)
def latex_matrix(m):
    return r'\begin{pmatrix}' + f'{m[0,0]:.6g} & {m[0,1]:.6g}' + r'\\' + f'{m[1,0]:.6g} & {m[1,1]:.6g}' + r'\end{pmatrix}'
st.latex(r'\begin{pmatrix}y_{\rm salida}\\\theta_{\rm salida}\end{pmatrix}=M\begin{pmatrix}y_{\rm entrada}\\\theta_{\rm entrada}\end{pmatrix},\qquad M=' + latex_matrix(mtotal))
st.latex(r'\begin{pmatrix}' + f'{mout[0]:.6g}' + r'\;\mathrm{mm}\\' + f'{mout[1]:.6g}' + r'\;\mathrm{rad}\end{pmatrix}=' + latex_matrix(mtotal) + r'\begin{pmatrix}' + f'{input_height:.6g}' + r'\\' + f'{input_theta:.6g}' + r'\end{pmatrix}')
st.caption('A y D son adimensionales; B está en mm y C en mm⁻¹. Con aire en entrada y salida, det(M)=1. Las matrices se multiplican en orden inverso al recorrido: la primera actuación queda a la derecha.')
if any(row['clipped'] for row in mrows):
    st.warning('Este rayo queda bloqueado por una abertura. La matriz muestra su prolongación matemática; después del bloqueo no representa luz transmitida.')
if abs(input_theta) > .1 or any(abs(row['theta']) > .1 for row in mrows):
    st.info('Hay ángulos superiores a 0,1 rad: comprueba la precisión con el trazado exacto. La matriz utiliza sin θ ≈ tan θ ≈ θ.')
st.dataframe([{'Superficie': row['name'], 'Espacio previo (mm)': row['distance'], 'n antes': row['n_before'], 'n después': row['n_after'], 'y salida (mm)': row['height'], 'θ salida (rad)': row['theta'], 'Estado': 'Prolongación tras bloqueo' if row['clipped'] else 'Admitido'} for row in mrows], hide_index=True, width='stretch')
with st.expander('Matrices de propagación e interacción, paso a paso'):
    st.latex(r'T(d)=\begin{pmatrix}1&d\\0&1\end{pmatrix},\quad S=\begin{pmatrix}1&0\\-\frac{n_2-n_1}{n_2R}&\frac{n_1}{n_2}\end{pmatrix}')
    st.markdown('Estas matrices usan **(y, θ)**. El motor gaussiano usa internamente **(y, nθ)**; se convierte de una base a otra en cada interfaz. En un espejo se invierte además la marcha física: la coordenada desplegada continúa creciendo. Una matriz identidad de espejo plano no significa transmisión.')
    for i, row in enumerate(mrows, 1):
        st.markdown(f'**{i}. {row["name"]}**')
        st.latex('T_{'+str(i)+'}='+latex_matrix(row['propagation'])+r',\quad S_{'+str(i)+'}='+latex_matrix(row['interface']))
    st.caption('M = Sₖ Tₖ … S₂ T₂ S₁ T₁. Las desviaciones matriciales se aplican en planos de vértice; el trazado exacto de la gráfica utiliza las superficies curvas y Snell, no estas matrices.')

export = dict(source_mode=source_mode, object_distance=(obj if finite_source else None), source_focus=(result['front_focus'] if source_mode == 'Desde el foco F' else None), object_height=height, placement=placement, reference_position=origin, initial_diameter=diameter, wavelength_nm=wavelength, elements=edited)
st.download_button('Descargar configuración JSON', json.dumps(export, ensure_ascii=False, indent=2), 'sistema-optico.json', 'application/json')
st.caption('Referencias: [OptiCampus · trazado de lentes delgadas](https://opticampus.opti.vision/cecourse.php?url=ray_tracing/) · [Edmund Optics · trazado paraxial](https://www.edmundoptics.com/knowledge-center/application-notes/optics/geometrical-optics-101-paraxial-ray-tracing-calculations/) · [LibreTexts · rayos de construcción](https://phys.libretexts.org/Bookshelves/University_Physics/Calculus-Based_Physics_%28Schnick%29/Volume_B%3A_Electricity_Magnetism_and_Optics/B28%3A_Thin_Lenses_-_Ray_Tracing) · [reflexión y Snell](https://www.pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission) · [matrices ABCD](https://www.rp-photonics.com/abcd_matrix.html) · [pupilas de entrada y salida](https://www.rp-photonics.com/entrance_and_exit_pupil.html)')
