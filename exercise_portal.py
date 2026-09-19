"""Student portal and inline Streamlit v2 canvas."""
from pathlib import Path
import hashlib
import math
import secrets
import streamlit as st
from exercises import generate_exercise, public_exercise, assess_exercise
from optics import Element

HTML = '''
<div class="exercise-root">
 <div class="toolbar"><label>Herramienta <select data-tool aria-label="Herramienta del canvas"></select></label>
 <button data-undo>Deshacer punto</button><button data-delete>Borrar selección</button>
 <button data-end-ray>Terminar rayo</button></div>
 <div class="toolbar"><label><input type="checkbox" data-snap checked> Ajustar a la superficie</label>
 <button data-zoom-in aria-label="Ampliar canvas">Zoom +</button><button data-zoom-out aria-label="Alejar canvas">Zoom −</button>
 <button data-reset>Limpiar canvas</button></div>
 <p data-readout aria-live="polite">Mueve el ratón por la cuadrícula para consultar coordenadas y ángulos.</p>
 <canvas tabindex="0" aria-label="Banco óptico del ejercicio: coloca elementos y traza rayos mediante clics"></canvas>
 <div class="toolbar"><span data-status></span><button data-finish>He terminado · revisar ejercicio</button></div>
</div>
'''
CSS = '''
.exercise-root {color:var(--st-text-color);font-family:var(--st-font);}
.toolbar {display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;margin:.5rem 0;}
button,select {font:inherit;color:var(--st-text-color);background:var(--st-secondary-background-color);border:1px solid var(--st-border-color,#b6c1cf);border-radius:.4rem;padding:.45rem .65rem;cursor:pointer;}
button:focus-visible,select:focus-visible,canvas:focus-visible {outline:2px solid var(--st-primary-color);outline-offset:2px;}
canvas {display:block;border:1px solid #cbd5e1;border-radius:.5rem;touch-action:manipulation;cursor:crosshair;}
[data-readout] {font-variant-numeric:tabular-nums;min-height:1.6em;margin:.5rem 0;}
[data-finish] {font-weight:600;border:2px solid var(--st-primary-color);margin-left:auto;}
'''
CANVAS_JS = Path(__file__).with_name('exercise_canvas.js').read_text()
# A new frontend bundle must not reuse a previously loaded component renderer.
CANVAS_VERSION = hashlib.sha256((HTML + CSS + CANVAS_JS).encode()).hexdigest()[:12]
CANVAS = st.components.v2.component('optical_exercise_canvas_' + CANVAS_VERSION,
    html=HTML, css=CSS, js=CANVAS_JS)


def render_exercise_portal():
    st.title('Taller de trazado de rayos')
    if st.button('Volver al banco óptico', key='back_to_simulator'):
        st.session_state.portal = 'simulator'
        st.rerun()
    st.write('Construye el banco indicado y traza los rayos pedidos. Cada clic fija un punto; un doble clic termina el rayo.')
    c1, c2 = st.columns([2, 1], vertical_alignment='bottom')
    count = c1.selectbox('Número de elementos ópticos', [1, 2, 3], key='exercise_count')
    new = c2.button('Generar ejercicio', key='generate_exercise')
    if new:
        st.session_state.exercise = generate_exercise(count, secrets.randbits(32))
        st.session_state.exercise_scene = dict(placements={}, rays=[], draft=[], tool='place:object')
        st.session_state.exercise_feedback = None
    if 'exercise' not in st.session_state:
        st.info('Elige uno, dos o tres elementos y pulsa «Generar ejercicio» para comenzar.')
        return
    ex = st.session_state.exercise
    if ex.get('mode') != 'chief_marginal' or ex.get('revision') != 'tip-v2':
        st.info('Pulsa «Generar ejercicio» para usar el enunciado actualizado: el principal y ambos marginales salen del extremo O. Tu ejercicio anterior no se sustituye hasta que lo generes.')
        return
    if count != len(ex['elements']):
        st.caption('Pulsa «Generar ejercicio» para aplicar el nuevo número de elementos.')
    st.header('Enunciado:')
    st.write(f'Sitúa el objeto O en **x = {ex["object_x"]:g} mm**, con altura **{ex["object_height"]:g} mm**. La luz sale inicialmente hacia la derecha. Coloca los siguientes elementos centrados en el eje:')
    properties=[]
    for data in ex['elements']:
        e=Element(**data)
        r1,r2=e.radii() if e.lens else (math.inf if e.kind=='Espejo plano' else (-abs(e.r1) if e.kind=='Espejo cóncavo' else abs(e.r1)), None)
        radius=lambda r: '—' if r is None else ('∞' if math.isinf(r) else f'{r:+g}')
        properties.append({'Elemento':e.name,'Tipo':e.kind,'Posición (mm)':e.position,'Altura / diámetro (mm)':e.aperture,'Grosor (mm)':e.thickness,'n':f'{e.index:g}' if e.lens else '—','R₁ (mm)':radius(r1),'R₂ (mm)':radius(r2)})
    st.dataframe(properties, hide_index=True, width='stretch')
    st.caption('Radios cartesianos: centro de curvatura a la derecha, R positivo; cara plana, R=∞. Aire exterior n=1; luz de 550 nm. No hay diafragmas. Un espejo, si aparece, es el último elemento y refleja toda la luz.')
    st.write('Los tres rayos salen del extremo O, a la altura del objeto; ninguno de los marginales se inicia en su base sobre el eje.')
    st.write('Traza estos rayos: '+ '; '.join(r['label'] for r in ex['rays'])+'.')
    with st.expander('Cómo resolver el ejercicio'):
        st.markdown('''1. Selecciona «Colocar objeto O» y haz clic en su posición sobre el eje. La altura está fijada por el enunciado.
2. Coloca E1, E2 y E3, según corresponda. Puedes recolocarlos seleccionándolos otra vez; al moverlos se borran los rayos anteriores.
3. Elige un tipo de rayo. El principal y los dos marginales parten del mismo extremo O del objeto, a la altura indicada en el enunciado. Los marginales delimitan por arriba y por abajo el haz admitido desde ese punto. Marca después cada punto de refracción o reflexión. Una lente gruesa exige dos puntos, uno por cara; en el retorno, repite las caras alcanzadas.
4. El segmento discontinuo sigue al ratón. Consulta altura y ángulo físico; la escala vertical del dibujo está ampliada. «Ajustar a la superficie» ayuda a colocar el punto sobre la curva sin calcular la dirección por ti.
5. Haz doble clic para fijar el extremo final, al menos 10 mm después de la última interacción. También puedes fijar el punto y pulsar «Terminar rayo».
6. Para prolongar un rayo hacia el espacio virtual, termínalo primero y selecciona «Prolongación virtual» para ese rayo. Mueve el cursor hacia atrás desde la última interacción y haz clic para fijar la longitud: la prolongación se dibuja discontinua sobre la recta de salida que tú has trazado.
7. Prolonga varios rayos y marca su cruce con «Marcar imagen virtual O′». Para hallar F′ usa rayos auxiliares que lleguen paralelos al eje; los rayos de un objeto finito determinan su imagen, no el foco. Dibuja esos rayos con «Dibujar rayo auxiliar» y prolonga después sus salidas. «Marcar foco virtual F′» coloca tu punto sobre el eje. Puedes marcar también un objeto virtual con Oᵥ. Usa «Zoom −» si el cruce queda fuera de la vista.
8. Las prolongaciones, los rayos auxiliares y las marcas son construcciones libres: se guardan con tu dibujo, pero no cuentan como interacciones y no se califican. Solo se revisan los rayos pedidos en el enunciado.
9. Pulsa «He terminado» y corrige los errores indicados. Puedes entregar de nuevo tantas veces como necesites.

**Teclado:** enfoca el canvas; las flechas desplazan el cursor, Intro coloca un punto, Mayús+Intro termina, Retroceso deshace y Escape cancela el rayo actual.''')
    st.caption(f'Tolerancias de revisión: posiciones e interacciones ±{ex["point_tolerance"]:g} mm; direcciones ±{ex["angle_tolerance"]:g}°. Las lentes conservan su diámetro útil: un rayo no puede atravesar una zona sin vidrio.')
    st.subheader('2 · Tu trazado')
    st.caption('El canvas empieza sin objeto, elementos, rayos ni referencias de la solución. La cuadrícula y el eje sirven para colocar tu propio dibujo; las correcciones aparecen debajo.')
    key='exercise_canvas_'+ex['id']
    previous=st.session_state.get(key, {})
    scene=previous.get('value', st.session_state.exercise_scene)
    feedback=st.session_state.get('exercise_feedback')
    # A changed construction invalidates the previous assessment immediately.
    if feedback and any(feedback.get('scene',{}).get(k) != scene.get(k) for k in ('placements','rays','draft','extensions','virtualPoints','auxiliary')):
        feedback=None
        st.session_state.exercise_feedback=None
    canvas = CANVAS(key=key, data=dict(exercise=public_exercise(ex), scene=scene),
                    on_value_change=lambda: None, on_submitted_change=lambda: None)
    if canvas.value is not None:
        st.session_state.exercise_scene=canvas.value
    if canvas.submitted is not None and (not feedback or feedback.get('scene')!=canvas.submitted):
        submitted=canvas.submitted
        report=assess_exercise(ex, submitted)
        st.session_state.exercise_scene=submitted
        st.session_state.exercise_feedback=dict(scene=submitted, report=report)
        st.rerun()
    feedback=st.session_state.get('exercise_feedback')
    if feedback:
        st.subheader('3 · Revisión')
        report=feedback['report']
        if report['correct']:
            st.success('Ejercicio correcto. Has colocado el banco y trazado todos los rayos dentro de las tolerancias.')
        else:
            st.warning('Revisa los pasos siguientes en orden. Primero corrige las posiciones; después, el primer error de cada rayo. Al entregar de nuevo se comprobará el recorrido actualizado.')
            for number, issue in enumerate(report['issues'], 1):
                st.markdown(f'**{number}.** {issue}')
        with st.expander('Lo que ya está bien', expanded=report['correct']):
            for item in report['passed']:
                st.write('✓ '+item)
