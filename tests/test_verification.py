"""Independent physical identities and the exact-to-paraxial limit."""
import math
import unittest
import numpy as np
from optics import Element, Surface, analyze, sag, translation
from raytrace import geometry, physical_paraxial, reflect, refract, trace_exact


class VerificationTests(unittest.TestCase):
    def test_snell_reversibility_and_reflection_rotated_normals(self):
        for rotation in np.linspace(-math.pi, math.pi, 13):
            normal = np.array([math.cos(rotation), math.sin(rotation)])
            tangent = np.array([-normal[1], normal[0]])
            for angle in [.0, .1, .4, .8, 1.2]:
                incident = math.cos(angle)*normal + math.sin(angle)*tangent
                outgoing, tir = refract(incident, normal, 1., 1.5)
                self.assertFalse(tir)
                self.assertAlmostEqual(np.dot(incident, tangent), 1.5*np.dot(outgoing, tangent))
                reverse, tir = refract(-outgoing, normal, 1.5, 1.)
                self.assertFalse(tir)
                np.testing.assert_allclose(reverse, -incident, atol=2e-14)
                np.testing.assert_allclose(reflect(reflect(incident, normal), normal), incident, atol=2e-14)

    def test_both_sides_of_critical_angle(self):
        critical = math.asin(1/1.5)
        for delta, expected in [(-1e-6, False), (1e-6, True)]:
            angle = critical + delta
            _, tir = refract([math.cos(angle), math.sin(angle)], [1, 0], 1.5, 1)
            self.assertEqual(tir, expected)

    def test_nearly_plane_sag_preserves_sign_and_small_height(self):
        for radius in [1e6, 1e10, 1e12, -1e12]:
            self.assertAlmostEqual(float(sag(radius, 1))/(1/(2*radius)), 1., places=11)

    def test_real_and_virtual_entrance_pupils_from_thin_lens_equation(self):
        # Stop is seen backwards through a f=50 lens at x=40.
        for separation in [25., 100.]:
            stop_x = 40 + separation
            ss = [Surface(0, 1000, np.eye(2), 'Reference', 1),
                  Surface(40, 1000, np.array([[1., 0.], [-1/50, 1.]]), 'Lens', 1),
                  Surface(stop_x, 2, np.eye(2), 'Stop', 1)]
            result = analyze(ss, -100)
            image_distance = 1/(1/50 - 1/separation)
            self.assertEqual(result['stop'], 2)
            self.assertAlmostEqual(result['entrance_x'], 40-image_distance)
            self.assertAlmostEqual(result['entrance_diameter'], 2*abs(image_distance/separation))
            self.assertAlmostEqual(result['exit_x'], stop_x)
            self.assertAlmostEqual(result['exit_diameter'], 2)

    def test_sixty_systems_exact_linearization_matches_gaussian_matrix(self):
        rng = np.random.default_rng(712)
        kinds = ['Biconvexa', 'Bicóncava', 'Menisco', 'Plano-convexa', 'Convexa-plana']
        for case in range(60):
            elements = [Element(name=f'L{j}', kind=str(rng.choice(kinds)), position=30+45*j,
                                aperture=8, thickness=4, index=rng.uniform(1.3, 1.9),
                                r1=rng.uniform(30, 200), r2=rng.uniform(30, 200))
                        for j in range(int(rng.integers(1, 4)))]
            if case % 2:
                elements.append(Element(name='M', kind=['Espejo plano', 'Espejo cóncavo', 'Espejo convexo'][case % 3],
                                        position=180, aperture=20, r1=200))
            with self.subTest(case=case):
                result = physical_paraxial(elements, 20, 550, -100)
                boundaries = geometry(elements, 20, 550)

                def exact_output(height, slope):
                    ray = trace_exact(boundaries, -100, height, math.atan(slope), -300, 400)
                    self.assertIsNone(ray['blocked'])
                    q, d = ray['exit_point'], ray['exit_direction']
                    return np.array([q[1]+(result['output_x']-q[0])*d[1]/d[0], d[1]/abs(d[0])])

                jacobian = np.column_stack([(exact_output(1e-4, 0)-exact_output(-1e-4, 0))/2e-4,
                                            (exact_output(0, 1e-6)-exact_output(0, -1e-6))/2e-6])
                expected = result['matrix'] @ translation(100)
                np.testing.assert_allclose(jacobian, expected, atol=3e-6, rtol=1e-7)
                self.assertAlmostEqual(np.linalg.det(result['matrix']), 1., places=11)
