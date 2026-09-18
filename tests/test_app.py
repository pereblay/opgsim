import json
import unittest
import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'app.py')

class AppTests(unittest.TestCase):
    def setUp(self):
        # Each AppTest has its own component registry. Re-import its declaration
        # rather than reusing a renderer registered in a previous test runtime.
        sys.modules.pop('exercise_portal', None)

    def test_presets_models_and_plot_conventions(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(app.exception)
        for preset in next(s for s in app.selectbox if s.label == 'Configuración').options:
            next(s for s in app.selectbox if s.label == 'Configuración').select(preset)
            next(b for b in app.button if b.label == 'Cargar ejemplo').click().run()
            for mode in ['Paraxial · aproximación matricial', 'Exacto · Snell y reflexión']:
                next(s for s in app.selectbox if s.label == 'Modelo de rayos').select(mode).run()
                self.assertFalse(app.exception, (preset, mode, app.exception))
                self.assertFalse(app.error, (preset, mode, app.error))
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
        for preset in next(s for s in app.selectbox if s.label == 'Configuración').options:
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
        self.assertEqual(ex['mode'],'chief_marginal')
        scene=solved(ex)
        app.session_state['exercise_canvas_'+ex['id']]={'value':scene,'submitted':scene}
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Ejercicio correcto' in s.value for s in app.success))

    def test_zero_default_and_complete_haz_from_tip_and_axis(self):
        app = AppTest.from_file(APP, default_timeout=30).run()
        height = next(w for w in app.number_input if w.label == 'Altura total del objeto (mm)')
        self.assertEqual(height.value, 0.)
        height.set_value(5.)
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
