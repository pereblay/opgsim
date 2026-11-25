import json
import unittest
import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest
from presets import BENCH_PRESETS, PRESETS

APP = str(Path(__file__).resolve().parents[1] / 'app.py')

class AppTests(unittest.TestCase):
    def setUp(self):
        # Each AppTest has its own component registry. Re-import its declaration
        # rather than reusing a renderer registered in a previous test runtime.
        sys.modules.pop('exercise_portal', None)

    def test_startup_refreshes_optics_cached_before_the_deployment(self):
        from unittest.mock import patch
        import optics

        with patch.object(optics, '_opgsim_revision', 'previous-release', create=True):
            del optics.CONIC_MIRRORS
            try:
                app = AppTest.from_file(APP, default_timeout=30).run()
                self.assertFalse(app.exception)
                element_types = next(s for s in app.selectbox if s.label == 'Tipo de elemento')
                self.assertIn('Espejo parabólico con abertura central', element_types.options)
            finally:
                if not hasattr(optics, 'CONIC_MIRRORS'):
                    from importlib import reload
                    reload(optics)

    def test_presets_models_and_plot_conventions(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(app.exception)
        for preset in PRESETS:
            next(s for s in app.selectbox if s.label == 'Configuración').select(preset)
            next(b for b in app.button if b.label == 'Cargar ejemplo').click().run()
            for mode in ['Paraxial · aproximación matricial', 'Exacto · Snell y reflexión']:
                next(s for s in app.selectbox if s.label == 'Modelo de rayos').select(mode).run()
                self.assertFalse(app.exception, (preset, mode, app.exception))
                self.assertFalse(app.error, (preset, mode, app.error))
                if app.session_state['elements']:
                    self.assertEqual(app.session_state['elements'][0]['position'],0.)
                plot = json.loads(app.get('plotly_chart')[1].proto.spec)
                self.assertFalse(any(a.get('showarrow', False) for a in plot['layout'].get('annotations', [])))
                self.assertEqual(plot['layout']['legend']['groupclick'], 'togglegroup')
                for t in plot['data']:
                    if t.get('opacity') == .4 or str(t.get('hovertemplate', '')).startswith('Interceptado:'):
                        self.assertTrue(t.get('legendgroup'))
                obj = next(t for t in plot['data'] if t.get('name') == 'O · Objeto real')
                self.assertNotEqual(obj['line'].get('dash'), 'dash')
                image = next(t for t in plot['data'] if t.get('name') == ('O′G · Imagen gaussiana' if mode.startswith('Exacto') else 'O′ · Imagen gaussiana'))
                self.assertEqual(image['line']['dash'], 'dash')
                if preset == 'Lente convergente':
                    labels = [a.get('text') for a in plot['layout']['annotations']]
                    for label in ['O', 'O′', 'F', 'F′', 'F1', 'F1′']:
                        self.assertIn(label+'G' if mode.startswith('Exacto') and label != 'O' else label, labels)
        print('All presets, both tracing models, O/O′ styles and focal labels verified.')

    def test_exercise_thin_lens_default_and_toggle(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        app.button(key='open_exercises').click().run()
        self.assertTrue(app.checkbox(key='exercise_thin_lens').value)
        app.button(key='generate_exercise').click().run()
        self.assertTrue(app.session_state['exercise']['thin_lens'])
        first_id = app.session_state['exercise']['id']
        app.checkbox(key='exercise_thin_lens').uncheck().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.session_state['exercise']['thin_lens'])
        app.checkbox(key='exercise_thin_lens').check().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['exercise']['thin_lens'])
        self.assertNotEqual(app.session_state['exercise']['id'], first_id)
        self.assertEqual(app.session_state['exercise_scene']['rays'], [])

    def test_aperture_stop_toggle(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        self.assertTrue(app.checkbox(key='auto_as').value)
        app.checkbox(key='auto_as').uncheck().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('AS fijado por el usuario: **Abertura inicial**' in i.value for i in app.info))
        app.checkbox(key='auto_as').check().run()
        self.assertTrue(any('AS automático:' in i.value for i in app.info))

    def test_signed_bank_positions_survive_edit_and_add(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        for x in (-30., 25.):
            app.session_state['editor_0'] = {
                'edited_rows': {0: {'position': x}}, 'added_rows': [], 'deleted_rows': []}
            app.run()
            self.assertEqual(app.session_state['elements'][0]['position'], x)
            self.assertFalse(app.error)
        next(w for w in app.number_input if w.label == 'Posición x en el banco (mm)').set_value(-45.)
        next(b for b in app.button if b.label == 'Añadir elemento').click().run()
        for mode in ['Paraxial · aproximación matricial', 'Exacto · Snell y reflexión']:
            next(w for w in app.selectbox if w.label == 'Modelo de rayos').select(mode).run()
            rows = app.session_state['elements']
            self.assertEqual([row['position'] for row in rows], [25., -45.])
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            plot = json.loads(app.get('plotly_chart')[0].proto.spec)
            labels = {a['text']: a['x'] for a in plot['layout']['annotations']}
            for row in rows:
                self.assertEqual(labels[row['name']], row['position'])

    def test_add_curvature_fields_match_faces(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        kind = lambda: next(w for w in app.selectbox if w.label == 'Tipo de elemento')
        kind().select('Lente personalizada').run()
        app.number_input(key='add_r1_Lente personalizada').set_value(-32.)
        app.number_input(key='add_r2_Lente personalizada').set_value(76.)
        next(b for b in app.button if b.label == 'Añadir elemento').click().run()
        self.assertFalse(app.error)
        added = app.session_state['elements'][-1]
        self.assertEqual((added['r1'], added['r2']), (-32., 76.))
        for name, sides in [('Plano-convexa', [2]), ('Convexa-plana', [1]), ('Espejo cóncavo', [1]),
                            ('Espejo plano', []), ('Diafragma', [])]:
            kind().select(name).run()
            self.assertEqual([w.key for w in app.number_input if (w.key or '').startswith('add_r')],
                             [f'add_r{i}_{name}' for i in sides])
            self.assertFalse(app.exception)

    def test_add_remove_preserves_configuration(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        next(b for b in app.button if b.label == 'Añadir elemento').click().run()
        self.assertEqual(len(app.session_state['elements']), 2)
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label == 'Eliminar seleccionado').click().run()
        self.assertEqual(len(app.session_state['elements']), 1)
        self.assertFalse(app.exception)

    def test_new_axial_sources_all_presets_and_models(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        for preset in PRESETS:
            next(s for s in app.selectbox if s.label == 'Configuración').select(preset)
            next(b for b in app.button if b.label == 'Cargar ejemplo').click().run()
            for source in ['Paralelos desde infinito', 'Desde el foco F']:
                next(r for r in app.radio if r.label == 'Origen de los rayos').set_value(source).run()
                for mode in ['Paraxial · aproximación matricial', 'Exacto · Snell y reflexión']:
                    next(s for s in app.selectbox if s.label == 'Modelo de rayos').select(mode).run()
                    self.assertFalse(app.exception, (preset, source, mode))
                    self.assertFalse(app.error, (preset, source, mode))
                    if source == 'Desde el foco F' and preset in ['Banco vacío', 'Espejo plano']:
                        self.assertTrue(any('afocal' in i.value for i in app.info))
                    else:
                        plot = json.loads(app.get('plotly_chart')[1].proto.spec)
                        rays = [t for t in plot['data'] if t.get('legendgroup')]
                        self.assertGreaterEqual(len(rays), 5)
                        self.assertFalse(any(a.get('showarrow', False) for a in plot['layout'].get('annotations', [])))
        next(r for r in app.radio if r.label == 'Origen de los rayos').set_value('Objeto finito').run()
        self.assertEqual(len(app.get('plotly_chart')), 2)

    def test_thin_lens_mode_collimates_the_two_lens_example(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        first = dict(app.session_state['elements'][0])
        second = dict(first, name='E2', position=70., r1=20., r2=-20.)
        app.session_state['elements'] = [first, second]
        next(r for r in app.radio if r.label == 'Origen de los rayos').set_value('Paralelos desde infinito')
        next(s for s in app.selectbox if s.label == 'Modelo de rayos').select('Paraxial · lente delgada').run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(any('Sistema afocal' in item.value for item in app.info))
        plot = json.loads(app.get('plotly_chart')[1].proto.spec)
        foci = {item['text']: item['x'] for item in plot['layout']['annotations']}
        for label, x in {'F1': -50., 'F1′': 50., 'F2': 50., 'F2′': 90.}.items():
            self.assertAlmostEqual(foci[label], x)
        for name, x in [('Lente', 0.), ('E2', 70.)]:
            trace = next(t for t in plot['data'] if t.get('name') == name)
            self.assertEqual(trace['x'], [x, x])
        self.assertEqual([row['thickness'] for row in app.session_state['elements']], [4., 4.])

    def test_add_ideal_lenses_with_entered_focal_length(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        for suffix, position, focal in [('convergente', 80., 35.), ('divergente', 140., 25.)]:
            kind = 'Lente delgada '+suffix
            next(s for s in app.selectbox if s.label == 'Tipo de elemento').select(kind).run()
            app.number_input(key=f'add_focal_{kind}').set_value(focal)
            next(w for w in app.number_input if w.label == 'Posición x en el banco (mm)').set_value(position)
            next(b for b in app.button if b.label == 'Añadir elemento').click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            row = app.session_state['elements'][-1]
            self.assertEqual((row['kind'], row['focal_length'], row['thickness']), (kind, focal, 0.))
        for mode in ['Exacto · Snell y reflexión', 'Paraxial · aproximación matricial',
                     'Paraxial · lente delgada']:
            next(s for s in app.selectbox if s.label == 'Modelo de rayos').select(mode).run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            table = next(item.value for item in app.dataframe
                         if 'Focal efectiva (mm)' in item.value.columns)
            self.assertEqual(table['Focal efectiva (mm)'].tolist()[1:3], ['35.000 mm', '-25.000 mm'])

    def test_folded_telescope_plot_includes_the_focus_behind_the_primary(self):
        from base64 import b64decode
        from dataclasses import asdict
        import numpy as np
        from optics import Element

        app = AppTest.from_file(APP, default_timeout=30).run()
        app.session_state['elements'] = [
            asdict(Element(name='Primario', kind='Espejo hiperbólico cóncavo con abertura central',
                           position=408.8393, aperture=200., central_opening=50., r1=920.,
                           conic_constant=-1.0022985)),
            asdict(Element(name='Secundario', kind='Espejo hiperbólico convexo',
                           position=0., aperture=23.417, r1=113.1667, conic_constant=-1.496,
                           invert_mirror=True)),
        ]
        next(w for w in app.number_input if w.label == 'Diámetro de abertura inicial (mm)').set_value(200.)
        next(r for r in app.radio if r.label == 'Origen de los rayos').set_value('Paralelos desde infinito').run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        traces = json.loads(app.get('plotly_chart')[1].proto.spec)['data']
        ray = next(trace for trace in traces if trace.get('name') == 'y=50 · Paralelo 4')
        coords = [np.frombuffer(b64decode(ray[axis]['bdata']), dtype=ray[axis]['dtype']) for axis in ('x', 'y')]
        x, y = coords
        self.assertGreater(x[-1], 533.84)
        self.assertLess(y[-1]*y[-2], 0.)

    def test_rotated_mirror_and_off_axis_ocular(self):
        from dataclasses import asdict
        from optics import Element

        app = AppTest.from_file(APP, default_timeout=30).run()
        app.session_state['elements'] = [
            asdict(Element(name='Primario', kind='Espejo cóncavo', position=500., r1=200., aperture=40.)),
            asdict(Element(name='Secundario', kind='Espejo plano', position=425., tilt=45., aperture=12.,
                           invert_mirror=True)),
            asdict(Element(name='Ocular', kind='Lente delgada convergente', position=425., height=50.,
                           tilt=90., aperture=20., focal_length=25.)),
        ]
        next(w for w in app.number_input if w.label == 'Diámetro de abertura inicial (mm)').set_value(40.)
        next(r for r in app.radio if r.label == 'Origen de los rayos').set_value('Paralelos desde infinito')
        next(s for s in app.selectbox if s.label == 'Modelo de rayos').select('Paraxial · lente delgada').run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(any('usa el trazado exacto' in item.value for item in app.info))
        interactions = next(item.value for item in app.dataframe if 'Interacción' in item.value.columns)
        self.assertIn('Bloqueo en cara no reflectora', interactions['Interacción'].values)
        ocular = interactions[interactions['Superficie'] == 'Ocular · lente delgada']
        self.assertFalse(ocular.empty)
        for y in ocular['y (mm)']:
            self.assertAlmostEqual(y, 50.)
        states = next(item.value for item in app.dataframe if 'Estado' in item.value.columns)
        for y in (-10., 10.):
            self.assertEqual(states.loc[states['Origen y (mm)'] == y, 'Estado'].item(), 'Sale a 90.0°')
        ray = ocular.iloc[0]['Rayo']
        self.assertEqual(interactions[interactions['Rayo'] == ray]['Superficie'].tolist(),
                         ['Primario', 'Secundario', 'Ocular · lente delgada'])

    def test_add_perforated_hyperbolic_mirror_from_the_form(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        kind = 'Espejo hiperbólico cóncavo con abertura central'
        next(s for s in app.selectbox if s.label == 'Tipo de elemento').select(kind).run()
        next(w for w in app.checkbox if w.label == 'Invertir cara reflectora').check()
        next(w for w in app.number_input if w.label == 'Constante cónica K').set_value(-2.5)
        next(w for w in app.number_input if w.label == 'Diámetro de abertura central (mm)').set_value(6.)
        next(b for b in app.button if b.label == 'Añadir elemento').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        row = app.session_state['elements'][-1]
        self.assertEqual((row['kind'], row['conic_constant'], row['central_opening'], row['invert_mirror']),
                         (kind, -2.5, 6., True))

    def test_complete_presets_load_with_ready_to_trace_settings(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        for name, example in BENCH_PRESETS.items():
            next(s for s in app.selectbox if s.label == 'Configuración').select(name)
            next(b for b in app.button if b.label == 'Cargar ejemplo').click().run()
            self.assertFalse(app.exception, name)
            self.assertFalse(app.error, name)
            self.assertEqual(app.radio(key='source_mode').value, 'Paralelos desde infinito')
            self.assertEqual(app.number_input(key='aperture_position').value, example['aperture_position'])
            self.assertEqual(app.number_input(key='aperture_diameter').value, example['aperture_diameter'])
            self.assertEqual(app.selectbox(key='ray_model').value, example['ray_model'])
            self.assertEqual(len(app.get('plotly_chart')), 2)
            if name.startswith('Telescopio refractor'):
                self.assertTrue(any('Sistema afocal' in row.value for row in app.info), name)
            elif name.startswith('Teleobjetivo'):
                focal = next(m for m in app.metric if m.label == 'Focal efectiva')
                self.assertEqual(focal.value, '250.000 mm')
                plot = json.loads(app.get('plotly_chart')[1].proto.spec)
                image = next(t for t in plot['data'] if t.get('name') == 'O′ · Imagen gaussiana')
                self.assertAlmostEqual(image['x'][0], 145.)
            else:
                rays = next(d.value for d in app.dataframe if 'Reflexiones' in d.value.columns)
                self.assertTrue(any(rays['Reflexiones'] == 2), name)
                if 'Ritchey' in name:
                    self.assertEqual(sum(rays['Reflexiones'] == 2), 6)

    def test_matrix_panel_element_and_input(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        self.assertTrue(next(s for s in app.selectbox if s.label == 'Modelo de rayos').value.startswith('Exacto'))
        next(s for s in app.selectbox if s.label == 'Recorrido matricial').set_value(1).run()
        app.number_input(key='matrix_theta').set_value(.01).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Equivalente matricial' in s.value for s in app.subheader))
        self.assertGreater(len(app.latex), 3)

    def test_exercise_navigation_preserves_simulator_and_exercise(self):
        app=AppTest.from_file(APP,default_timeout=30).run()
        original=list(app.session_state['elements'])
        app.button(key='open_exercises').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value,'Taller de trazado de rayos')
        app.selectbox(key='exercise_count').set_value(3)
        app.button(key='generate_exercise').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['exercise']['elements']),3)
        exercise_id=app.session_state['exercise']['id']
        app.button(key='back_to_simulator').click().run()
        self.assertEqual(app.session_state['elements'],original)
        app.button(key='open_exercises').click().run()
        self.assertEqual(app.session_state['exercise']['id'],exercise_id)

    def test_exercise_success_and_no_construction_option(self):
        from tests.test_exercises import solved
        app=AppTest.from_file(APP,default_timeout=30).run()
        families=next(s for s in app.multiselect if s.label=='Rayos que se dibujan')
        self.assertNotIn('Construcción',families.options)
        app.button(key='open_exercises').click().run()
        self.assertFalse(any(s.label=='Modalidad del ejercicio' for s in app.selectbox))
        app.button(key='generate_exercise').click().run()
        ex=app.session_state['exercise']
        self.assertEqual(ex['mode'],'parallel_focal')
        scene=solved(ex)
        app.session_state['exercise_canvas_'+ex['id']]={'value':scene,'submitted':scene}
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Ejercicio correcto' in s.value for s in app.success))

    def test_default_ray_families_and_complete_haz_from_tip_and_axis(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        height = next(w for w in app.number_input if w.label == 'Altura total del objeto (mm)')
        self.assertEqual(height.value, 5.)
        mode_select = next(w for w in app.selectbox if w.label == 'Modelo de rayos')
        for mode in mode_select.options:
            mode_select.select(mode).run()
            self.assertFalse(app.exception)
            plot = json.loads(app.get('plotly_chart')[1].proto.spec)
            names = [t.get('name', '') for t in plot['data']]
            for label in ['Principal · centro del stop', 'Marginal − · borde útil',
                          'Marginal + · borde útil', 'Paralelo al eje', 'Rayo focal']:
                self.assertTrue(any(name.startswith('y=5 · ') and label in name for name in names))
            axial = [name for name in names if name.startswith('y=0 · Principal')]
            self.assertEqual(len(axial), 1)
            self.assertIn('Paralelo al eje / Rayo focal', axial[0])
        height.set_value(0.).run()
        names = [t.get('name', '') for t in json.loads(app.get('plotly_chart')[1].proto.spec)['data']]
        self.assertIn('y=0 · Principal · centro del stop / Paralelo al eje / Rayo focal · dirigido hacia F', names)
        next(w for w in app.number_input if w.label == 'Altura total del objeto (mm)').set_value(5.)
        next(s for s in app.selectbox if s.label == 'Modelo de rayos').select('Exacto · Snell y reflexión')
        next(w for w in app.multiselect if w.label == 'Rayos que se dibujan').set_value(['Haz']).run()
        self.assertFalse(app.exception)
        plot = json.loads(app.get('plotly_chart')[1].proto.spec)
        names = [t.get('name','') for t in plot['data']]
        for y in [0,5]:
            self.assertIn(f'y={y} · Marginal − · borde útil', names)
            self.assertIn(f'y={y} · Marginal + · borde útil', names)
        self.assertFalse(any(str(t.get('hovertemplate','')).startswith('Interceptado:') for t in plot['data']))
        self.assertEqual(sum(n.startswith('O′ · haz') for n in names), 2)
        next(w for w in app.multiselect if w.label == 'Rayos que se dibujan').set_value(['Principal y marginales']).run()
        names = [t.get('name','') for t in json.loads(app.get('plotly_chart')[1].proto.spec)['data']]
        for y in [0,5]:
            for label in ['Principal · centro del stop', 'Marginal − · borde útil', 'Marginal + · borde útil']:
                self.assertIn(f'y={y} · {label}', names)
