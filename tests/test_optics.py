import math
import unittest
import numpy as np
from optics import Element, Surface, build, analyze, trace, translation, admitted_interval

class OpticsTests(unittest.TestCase):
    def thin(self, f=50, stop=20):
        return [Surface(0, stop, np.eye(2), 'Entrada', 1),
                Surface(40, 100, np.array([[1., 0], [-1/f, 1.]]), 'Lente', 1)]

    def test_thin_lens_conjugate(self):
        r = analyze(self.thin(), -60)
        self.assertAlmostEqual(r['focal'], 50)
        self.assertAlmostEqual(r['image_x'], 140)
        self.assertAlmostEqual(r['magnification'], -1)
        self.assertAlmostEqual(r['h1'], 40)
        self.assertAlmostEqual(r['h2'], 40)
        self.assertAlmostEqual(r['front_focus'], -10)

    def test_thick_lens_lensmaker(self):
        r = analyze(build([Element(index=1.5)], 25, 550), -120)
        power = .5*(1/50 - 1/-50 + .5*4/(1.5*50*-50))
        self.assertAlmostEqual(r['focal'], 1/power)
        self.assertAlmostEqual(np.linalg.det(r['matrix']), 1)

    def test_empty_bank(self):
        r = analyze(build([], 10, 550), -100)
        self.assertIsNone(r['focal'])
        self.assertAlmostEqual(r['image_x'], -100)
        self.assertAlmostEqual(r['entrance_x'], 0)
        self.assertAlmostEqual(r['exit_diameter'], 10)

    def test_exit_pupil_and_stop_selection(self):
        ss = self.thin(stop=100)
        ss.append(Surface(65, 5, np.eye(2), 'Stop', 1))
        r = analyze(ss, -60)
        self.assertEqual(r['stop'], 2)
        self.assertAlmostEqual(r['entrance_x'], 90)
        self.assertAlmostEqual(r['entrance_diameter'], 10)
        self.assertAlmostEqual(r['exit_x'], 65)
        self.assertAlmostEqual(r['exit_diameter'], 5)

    def test_pupil_at_infinity(self):
        ss = self.thin()
        ss[1].x = 50
        r = analyze(ss, -100)
        self.assertIsNone(r['exit_x'])
        self.assertIsNone(r['exit_diameter'])

    def test_collimated_output(self):
        r = analyze(self.thin(), -10)
        self.assertIsNone(r['image_x'])
        self.assertIsNone(r['magnification'])

    def test_mirror_focus(self):
        for kind, f in [('Espejo cóncavo', 50), ('Espejo convexo', -50)]:
            ss = build([Element(kind=kind, r1=100)], 25, 550)
            self.assertAlmostEqual(analyze(ss, -100)['focal'], f)

    def test_unit_index_and_dispersion(self):
        self.assertIsNone(analyze(build([Element()], 25, 550), -120)['focal'])
        e = Element(index=1.5, dispersion=.004)
        self.assertAlmostEqual(e.n(550), 1.5)
        self.assertGreater(e.n(450), e.n(650))

    def test_clipping_and_interval(self):
        ss = build([], 10, 550)
        self.assertEqual(admitted_interval(ss, -100, 0), (-.05, .05))
        self.assertIsNotNone(trace(ss, -100, 0, .1, 100)['blocked'])
        self.assertIsNone(trace(ss, -100, 0, .05, 100)['blocked'])

    def test_invalid_geometry(self):
        for es in [[Element(position=-1)], [Element(thickness=-.01, index=1.5)],
                   [Element(), Element(position=41)], [Element(r1=0)],
                   [Element(index=float('nan'))]]:
            with self.assertRaises(ValueError):
                build(es, 25, 550)

    def test_rays_meet_image(self):
        ss = build([Element(index=1.5)], 25, 550)
        r = analyze(ss, -120)
        for h in [0, 2]:
            low, high = admitted_interval(ss, -120, h)
            for angle in np.linspace(low, high, 3):
                ray = trace(ss, -120, h, angle, r['image_x'])
                self.assertIsNone(ray['blocked'])
                self.assertAlmostEqual(ray['y'][-1], h*r['magnification'])

if __name__ == '__main__':
    unittest.main()

class MatrixWalkthroughTests(unittest.TestCase):
    def test_theta_basis_matches_reduced_basis_with_return(self):
        from raytrace import physical_paraxial
        from optics import matrix_walkthrough
        es = [Element(index=1.5), Element(kind='Espejo cóncavo', position=100, r1=150)]
        r = physical_paraxial(es, 30, 550, -100)
        m, state, rows = matrix_walkthrough(r['path'], 1., .002)
        np.testing.assert_allclose(m, r['matrix'], atol=1e-12)
        np.testing.assert_allclose(state, m @ [1., .002])
        self.assertTrue(any(row['n_after'] == 1.5 for row in rows))

    def test_plane_refraction_changes_theta(self):
        from optics import matrix_walkthrough
        ss = [Surface(0, 20, np.eye(2), 'Plane', 1.5)]
        m, state, rows = matrix_walkthrough(ss, 1, .06)
        self.assertAlmostEqual(state[1], .04)
        self.assertAlmostEqual(np.linalg.det(m), 1/1.5)
