"""Student portal and inline Streamlit v2 canvas."""
from pathlib import Path
import hashlib
import math
import secrets
import streamlit as st
from exercises import generate_exercise, public_exercise, assess_exercise
from optics import Element
from raytrace import physical_paraxial

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
    thin_lens = st.checkbox('Aproximación de lente delgada', value=st.session_state.get('exercise', {}).get('thin_lens', True), key='exercise_thin_lens',
                            help='Un único plano por lente y trazado paraxial. Al cambiar el modelo se reinicia el dibujo del ejercicio.')
    c1, c2 = st.columns([2, 1], vertical_alignment='bottom')
    count = c1.selectbox('Número de elementos ópticos', [1, 2, 3], key='exercise_count')
    new = c2.button('Generar ejercicio', key='generate_exercise')
    previous_exercise = st.session_state.get('exercise')
    model_changed = previous_exercise is not None and previous_exercise.get('thin_lens', False) != thin_lens
    if new or model_changed:
        seed = secrets.randbits(32) if new else previous_exercise['seed']
        st.session_state.exercise = generate_exercise(count, seed, thin_lens=thin_lens)
        st.session_state.exercise['id'] += '-'+secrets.token_hex(4)
        st.session_state.exercise_scene = dict(placements={}, rays=[], draft=[], tool='place:object')
        st.session_state.exercise_feedback = None
    if 'exercise' not in st.session_state:
        st.info('Elige uno, dos o tres elementos y pulsa «Generar ejercicio» para comenzar.')
        return
    ex = st.session_state.exercise
    if ex.get('mode') != 'parallel_focal' or ex.get('revision') != 'thin-v4':
        st.info('Pulsa «Generar ejercicio» para practicar chief, paralelo y focal con el primer elemento en x=0. Tu dibujo anterior se conserva hasta entonces.')
        return
    if count != len(ex['elements']):
        st.caption('Pulsa «Generar ejercicio» para aplicar el nuevo número de elementos.')
    st.caption('Modelo activo: lentes delgadas y espejos paraxiales; una interacción por elemento y por paso.' if ex['thin_lens'] else 'Modelo activo: superficies reales, Snell y reflexión exacta; dos caras por lente.')
    st.header('Enunciado:')
    st.write(f'Sitúa el objeto O en **x = {ex["object_x"]:g} mm**, con altura **{ex["object_height"]:g} mm**. La luz sale inicialmente hacia la derecha. Coloca los siguientes elementos centrados en el eje:')
    properties=[]
    for data in ex['elements']:
        e=Element(**data)
        r1,r2=e.radii() if e.lens else (math.inf if e.kind=='Espejo plano' else (-abs(e.r1) if e.kind=='Espejo cóncavo' else abs(e.r1)), None)
        radius=lambda r: '—' if r is None else ('∞' if math.isinf(r) else f'{r:+g}')
        focal=physical_paraxial([e],100,550,ex['object_x'], thin_lens=ex['thin_lens'])['focal']
        focal_text = '∞' if focal is None else f'{-focal:+.3f}'
        st.markdown(f'**{e.name} · {e.kind} — Focal objeto f = {focal_text} mm**')
        properties.append({'Elemento':e.name,'Tipo':e.kind,'f (mm)':focal_text,'Posición (mm)':e.position,'Altura / diámetro (mm)':e.aperture,'Grosor del modelo (mm)':0. if ex['thin_lens'] and e.lens else e.thickness,'n':f'{e.index:g}' if e.lens else '—','R₁ (mm)':radius(r1),'R₂ (mm)':radius(r2)})
    st.dataframe(properties, hide_index=True, width='stretch')
    st.caption('Radios cartesianos: centro de curvatura a la derecha, R positivo; cara plana, R=∞. Aire exterior n=1; luz de 550 nm. No hay diafragmas. Un espejo, si aparece, es el último elemento y refleja toda la luz.')
    st.write('Los tres rayos salen del mismo extremo O: chief al centro del stop, paralelo al eje y focal dirigido hacia F. Las focales de la tabla son distancias de cada elemento aislado, no sus coordenadas ni la focal del conjunto.')
    st.caption('f es la distancia focal objeto cartesiana, medida desde el plano principal al foco F, positiva hacia la derecha: negativa en lentes convergentes y espejos cóncavos; positiva en lentes divergentes y espejos convexos.')
    if ex['thin_lens']:
        st.caption('Para lentes en aire, usando la f de la tabla: θ_salida = θ_entrada + y/f. En un retorno se usa el eje local orientado en el sentido de propagación.')
    st.write('Traza estos rayos: '+ '; '.join(r['label'] for r in ex['rays'])+'.')
    with st.expander('Cómo resolver el ejercicio'):
        st.markdown('''1. Selecciona «Colocar objeto O» y haz clic en su posición sobre el eje. La altura está fijada por el enunciado.
2. E1 ya está fijado en x=0. Coloca E2 y E3 cuando aparezcan. Puedes recolocarlos seleccionándolos otra vez; al moverlos se borran los rayos anteriores.
3. Elige un tipo de rayo. El chief, el paralelo y el focal parten del mismo extremo O. El paralelo entra horizontal; el focal apunta al foco anterior F del sistema (o a su prolongación). En lentes gruesas, la focal se mide desde los planos principales. En el modelo paraxial, el rayo focal sale paralelo. Con la aproximación desactivada, la revisión aplica Snell en cada cara y puede aparecer aberración. Marca después cada punto de refracción o reflexión. Con la aproximación de lente delgada, marca un solo punto en el plano de cada lente; los espejos se tratan también paraxialmente en su plano de vértice. Al desactivarla, una lente gruesa exige dos puntos, uno por cara. En el retorno, repite las interacciones alcanzadas.
4. El segmento discontinuo sigue al ratón. Consulta altura y ángulo físico; la escala vertical del dibujo está ampliada. «Ajustar a la superficie» ayuda a colocar el punto sobre la curva sin calcular la dirección por ti.
5. Haz doble clic para fijar el extremo final, al menos 10 mm después de la última interacción. También puedes fijar el punto y pulsar «Terminar rayo».
6. Al terminar dos rayos, sus salidas se prolongan automáticamente con líneas discontinuas si se cruzan hacia atrás. Para ajustar una prolongación manualmente, selecciona «Prolongación virtual» para ese rayo. Mueve el cursor hacia atrás desde la última interacción y haz clic para fijar la longitud: la prolongación se dibuja discontinua sobre la recta de salida que tú has trazado.
7. Prolonga varios rayos y marca su cruce con «Marcar imagen virtual O′». Para hallar F′ usa rayos auxiliares que lleguen paralelos al eje; los rayos de un objeto finito determinan su imagen, no el foco. Dibuja esos rayos con «Dibujar rayo auxiliar» y prolonga después sus salidas. «Marcar foco F» permite señalar el foco objeto; «Marcar foco virtual F′», el foco imagen virtual. Ambas marcas se sitúan sobre el eje óptico. Usa «Zoom −» si el cruce queda fuera de la vista.
8. Las prolongaciones, los rayos auxiliares y las marcas son construcciones libres: se guardan con tu dibujo, pero no cuentan como interacciones y no se califican. Solo se revisan los rayos pedidos en el enunciado.
9. Pulsa «He terminado» y corrige los errores indicados. Puedes entregar de nuevo tantas veces como necesites.

**Teclado:** enfoca el canvas; las flechas desplazan el cursor, Intro coloca un punto, Mayús+Intro termina, Retroceso deshace y Escape cancela el rayo actual.''')
    st.caption(f'Tolerancias de revisión: posiciones e interacciones ±{ex["point_tolerance"]:g} mm; direcciones ±{ex["angle_tolerance"]:g}°. Las lentes conservan su diámetro útil: un rayo no puede atravesar una zona sin vidrio.')
    st.subheader('2 · Tu trazado')
    if ex['thin_lens']:
        st.caption('Lentes delgadas: símbolos hacia fuera (↑ arriba, ↓ abajo) para convergentes; hacia dentro para divergentes. Una lente de potencia nula se muestra sin símbolos.')
    st.caption('El primer elemento está fijado en x=0; el canvas no muestra focos ni rayos de solución. La cuadrícula y el eje sirven para colocar tu propio dibujo; las correcciones aparecen debajo.')
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
