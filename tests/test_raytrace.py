import math
import unittest
import numpy as np
from optics import Element
from raytrace import reflect, refract, geometry, physical_paraxial, trace_exact


class ExactRayTests(unittest.TestCase):
    def trace(self, elements, y=0., angle=0.):
        return trace_exact(geometry(elements, 100, 550), -120, y, angle, -180, 300)

    def test_plane_mirror_reverses_and_equal_angles(self):
        ray = self.trace([Element(kind='Espejo plano', position=50, aperture=80)], angle=.12)
        events = [e for e in ray['events'] if e['event'].startswith('Reflexión')]
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertAlmostEqual(e['incidence'], e['outgoing_angle'])
        self.assertAlmostEqual(e['incoming'][0], -e['outgoing'][0])
        self.assertAlmostEqual(e['incoming'][1], e['outgoing'][1])
        self.assertLess(ray['x'][-1], 50)
        self.assertTrue(all(x <= 50 for x in ray['x']))

    def test_plane_mirror_normal_incidence_returns(self):
        ray = self.trace([Element(kind='Espejo plano', position=50)], y=2)
        np.testing.assert_allclose(ray['exit_direction'], [-1, 0])
        np.testing.assert_allclose(ray['y'], 2)

    def test_snell_oblique(self):
        d, tir = refract([math.cos(.5), math.sin(.5)], [1, 0], 1, 1.5)
        self.assertFalse(tir)
        self.assertAlmostEqual(math.sin(.5), 1.5*d[1])
        self.assertLess(math.atan2(d[1], d[0]), .5)

    def test_normal_refraction_and_equal_indices(self):
        np.testing.assert_allclose(refract([1, 0], [1, 0], 1, 1.5)[0], [1, 0])
        d = np.array([math.cos(.5), math.sin(.5)])
        np.testing.assert_allclose(refract(d, [1, 0], 1, 1)[0], d)

    def test_total_internal_reflection(self):
        d, tir = refract([.5, math.sqrt(3)/2], [1, 0], 1.5, 1)
        self.assertTrue(tir)
        self.assertLess(d[0], 0)
        self.assertAlmostEqual(np.linalg.norm(d), 1)

    def test_thick_lens_snell_each_face(self):
        ray = self.trace([Element(index=1.5)], y=3)
        ev = [e for e in ray['events'] if e['event'] == 'Refracción']
        self.assertEqual(len(ev), 2)
        for e in ev:
            self.assertAlmostEqual(e['n_before']*math.sin(math.radians(e['incidence'])), e['n_after']*math.sin(math.radians(e['outgoing_angle'])))
            self.assertGreater(np.linalg.norm(e['incoming']-e['outgoing']), 1e-5)
        self.assertLess(ray['exit_direction'][1], 0)

    def test_mirror_retraces_lens_in_reverse_order(self):
        lens = Element(index=1.5)
        mirror = Element(name='Espejo', kind='Espejo plano', position=100, aperture=40)
        ray = self.trace([lens, mirror], y=.5)
        names = [e['surface'] for e in ray['events'] if e['event']=='Refracción']
        self.assertEqual(names, ['Lente · cara 1', 'Lente · cara 2', 'Lente · cara 2', 'Lente · cara 1'])
        self.assertEqual(ray['events'][-1]['n_after'], 1)
        self.assertLess(ray['exit_direction'][0], 0)

    def test_concave_and_convex_mirror_focus(self):
        for kind, focus in [('Espejo cóncavo', 0.), ('Espejo convexo', 100.)]:
            e = Element(kind=kind, position=50, r1=100)
            ray = self.trace([e], y=.001)
            reflection = next(ev for ev in ray['events'] if 'Reflexión' in ev['event'])
            q, d = reflection['point'], reflection['outgoing']
            axis_x = q[0]-q[1]*d[0]/d[1]
            self.assertAlmostEqual(axis_x, focus, places=5)

    def test_plane_mirror_virtual_image(self):
        r = physical_paraxial([Element(kind='Espejo plano', position=50)], 100, 550, -120)
        self.assertAlmostEqual(r['image_x'], 220)
        self.assertAlmostEqual(r['magnification'], 1)
        self.assertFalse(r['image_real'])

    def test_double_pass_paraxial_matches_small_exact_ray(self):
        es = [Element(index=1.5), Element(name='M', kind='Espejo plano', position=100, aperture=40)]
        r = physical_paraxial(es, 100, 550, -120)
        ray = self.trace(es, y=0., angle=.00001)
        q, d = ray['exit_point'], ray['exit_direction']
        image_x = q[0]-q[1]*d[0]/d[1]
        self.assertAlmostEqual(image_x, r['image_x'], places=4)

    def test_element_behind_mirror_not_reached(self):
        es = [Element(name='M', kind='Espejo plano', position=30), Element(name='Detrás', position=80, index=1.5)]
        ray = self.trace(es, y=1)
        self.assertFalse(any('Detrás' in ev['surface'] for ev in ray['events']))

    def test_hits_actual_sphere(self):
        e = Element(index=1.5)
        ray = self.trace([e], y=3)
        p = next(ev['point'] for ev in ray['events'] if ev['event']=='Refracción')
        self.assertAlmostEqual((p[0]-(e.position+50))**2+p[1]**2, 50**2)
        self.assertGreater(p[0], e.position)

class ReferenceTests(unittest.TestCase):
    def test_edmund_pcx_bfl(self):
        # Edmund Optics, PCX #49-849: R=26.25 mm, CT=5 mm,
        # n=1.517 as rounded in their worked ray-tracing example.
        e = Element(kind='Convexa-plana', position=25, aperture=25.4, thickness=5, index=1.517, r1=26.25)
        r = physical_paraxial([e], 30, 550, -120)
        self.assertAlmostEqual(r['back_focus_vertex'], 47.48, delta=.01)
        self.assertAlmostEqual(r['focal'], 26.25/.517)

    def test_cardinal_construction_rays(self):
        from raytrace import construction_rays, trace_gaussian
        for kind in ['Biconvexa', 'Bicóncava']:
            es = [Element(kind=kind, index=1.5)]
            r = physical_paraxial(es, 100, 550, -120)
            for name, slope in construction_rays(r, -120, .5):
                ray = trace_gaussian(r, -120, .5, slope, -200, 300)
                self.assertIsNone(ray['blocked'])
                q, d = ray['exit_point'], ray['exit_direction']
                self.assertAlmostEqual(q[1]+(r['image_x']-q[0])*d[1]/d[0], .5*r['magnification'])
                if name.startswith('Por F'):
                    self.assertAlmostEqual(d[1], 0)
                if name.startswith('Nodal'):
                    self.assertAlmostEqual(d[1]/d[0], slope)

    def test_mirror_focal_positions(self):
        from raytrace import focal_points
        for kind, position in [('Espejo cóncavo', 0), ('Espejo convexo', 100)]:
            f = focal_points([Element(kind=kind, position=50, r1=100)], 30, 550, -120)
            for row in f:
                self.assertAlmostEqual(row['front'], position)
                self.assertAlmostEqual(row['back'], position)

    def test_image_before_passive_exit_aperture_is_real(self):
        es = [Element(kind='Espejo cóncavo', position=100, r1=100)]
        r = physical_paraxial(es, 100, 550, -120)
        self.assertGreater(r['image_x'], 0)
        self.assertLess(r['image_x'], 100)
        self.assertTrue(r['image_real'])

    def test_paraxial_mirror_turns_back(self):
        from raytrace import trace_gaussian
        es = [Element(kind='Espejo plano', position=50, aperture=80)]
        r = physical_paraxial(es, 100, 550, -120)
        ray = trace_gaussian(r, -120, 1., .01, -180, 300)
        self.assertLess(ray['exit_direction'][0], 0)
        self.assertTrue(all(x <= 50 for x in ray['x']))
        q, d = ray['exit_point'], ray['exit_direction']
        self.assertAlmostEqual(q[1]+(r['image_x']-q[0])*d[1]/d[0], 1.)

class AxialSourceTests(unittest.TestCase):
    def test_infinity_and_focus_conjugates_and_ray_directions(self):
        from raytrace import axial_source_bundle, trace_gaussian
        systems = [[Element(index=1.5)], [Element(kind='Bicóncava', index=1.5)],
                   [Element(kind='Espejo cóncavo', position=50, r1=100)],
                   [Element(index=1.5), Element(kind='Espejo plano', position=100)]]
        for elements in systems:
            infinity = physical_paraxial(elements, 25, 550, None)
            self.assertAlmostEqual(infinity['image_x'], infinity['output_x']+infinity['output_direction']*infinity['back_focus'])
            self.assertIsNone(infinity['magnification'])
            for source in ['infinity', 'focus']:
                result = infinity if source == 'infinity' else physical_paraxial(elements, 25, 550, infinity['front_focus'])
                if source == 'focus':
                    self.assertIsNone(result['image_x'])
                x, rays = axial_source_bundle(result, source, 5, -80)
                for height, slope in rays:
                    ray = trace_gaussian(result, x, height, slope, -200, 400)
                    self.assertIsNone(ray['blocked'])
                    q, d = ray['exit_point'], ray['exit_direction']
                    if source == 'focus':
                        self.assertAlmostEqual(d[1], 0., places=10)
                    else:
                        self.assertEqual(slope, 0.)
                        self.assertAlmostEqual(q[1]+(result['image_x']-q[0])*d[1]/d[0], 0., places=10)

    def test_afocal_parallel_source_and_missing_focus(self):
        from raytrace import axial_source_bundle
        result = physical_paraxial([], 25, 550, None)
        self.assertIsNone(result['image_x'])
        x, rays = axial_source_bundle(result, 'infinity', 5, -80)
        self.assertTrue(all(slope == 0 for _, slope in rays))
        with self.assertRaisesRegex(ValueError, 'afocal'):
            axial_source_bundle(result, 'focus', 5, -80)

class SurfacePrecisionTests(unittest.TestCase):
    def test_nearly_plane_sphere_intersection(self):
        from raytrace import Boundary
        for radius in [50., -50., 1e12, -1e12]:
            from optics import sag
            boundary = Boundary(40., radius, 20., 'Surface')
            for sign in [-1., 1.]:
                point = np.array([40.-sign*100., 3.])
                hit = boundary.intersect(point, np.array([sign, 0.]))
                self.assertIsNotNone(hit)
                self.assertAlmostEqual(hit[1][0], 40+float(sag(radius, 3.)), places=10)

    def test_all_direction_changes_on_surfaces(self):
        es = [Element(index=1.5), Element(kind='Espejo cóncavo', position=100, aperture=40, r1=150)]
        boundaries = geometry(es, 30, 550)
        ray = trace_exact(boundaries, -100, 1., .01, -200, 300)
        for event in ray['events']:
            if event['event'] in ['Refracción', 'Reflexión (100 %)']:
                boundary = next(b for b in boundaries if b.name == event['surface'])
                from optics import sag
                self.assertAlmostEqual(event['point'][0], boundary.x+float(sag(boundary.radius, event['point'][1])), places=10)
                self.assertTrue(any(np.linalg.norm(event['point']-np.array([x,y])) < 1e-10 for x,y in zip(ray['x'],ray['y'])))

class ExactMarginalTests(unittest.TestCase):
    def test_real_marginals_continue_past_lenses_and_mirrors(self):
        from optics import admitted_interval
        from raytrace import exact_axial_aperture_scale
        from presets import PRESETS
        for name, elements in PRESETS.items():
            r=physical_paraxial(elements,25,550,-120)
            boundaries=geometry(elements,25,550)
            slope=admitted_interval(r['path'],-120,0)[1]
            scale=exact_axial_aperture_scale(boundaries,-120,0,slope,-300,400)
            for sign in [-1,1]:
                ray=trace_exact(boundaries,-120,0,math.atan(sign*slope*scale),-300,400)
                self.assertIsNone(ray['blocked'],name)
                self.assertAlmostEqual(ray['x'][-1],-300 if r['output_direction']<0 else 400,places=7)
            outside=trace_exact(boundaries,-120,0,math.atan(slope*scale*1.001),-300,400)
            self.assertIsNotNone(outside['blocked'],name)

    def test_parallel_and_focal_bundle_edges_continue(self):
        from raytrace import axial_source_bundle, exact_axial_aperture_scale
        for kind in ['Biconvexa','Bicóncava','Espejo cóncavo']:
            elements=[Element(kind=kind,index=1.5,r1=100,r2=-100)]
            r=physical_paraxial(elements,25,550,-120)
            boundaries=geometry(elements,25,550)
            for source in ['infinity','focus']:
                x,rays=axial_source_bundle(r,source,5,-80)
                h,u=rays[-1]
                scale=exact_axial_aperture_scale(boundaries,x,h,u,-300,400)
                for sign in [-1,1]:
                    ray=trace_exact(boundaries,x,sign*h*scale,math.atan(sign*u*scale),-300,400)
                    self.assertIsNone(ray['blocked'],(kind,source))

class BorderRegressionTests(unittest.TestCase):
    def test_thin_caps_and_small_radii_are_trimmed_consistently(self):
        from optics import build, sag
        for kind in ['Biconvexa', 'Bicóncava', 'Menisco', 'Convexa-plana', 'Espejo cóncavo']:
            for radius in [.1, 2., 50.]:
                e = Element(kind=kind, thickness=.1, r1=radius, r2=-radius, index=1.5)
                aperture = e.clear_aperture
                self.assertLessEqual(aperture, min(e.aperture, 2*radius))
                self.assertGreater(aperture, 0.)
                surfaces = build([e], 25, 550)
                self.assertAlmostEqual(surfaces[1].aperture, aperture)
                boundaries = geometry([e], 25, 550)
                self.assertAlmostEqual(boundaries[1].aperture, aperture)
                if e.lens:
                    yy = np.linspace(-aperture/2, aperture/2, 101)
                    r1, r2 = e.radii()
                    self.assertGreaterEqual(np.min(e.thickness+sag(r2, yy)-sag(r1, yy)), -1e-12)
                ray = trace_exact(boundaries, -120, 0, 0, -300, 400)
                self.assertIsNone(ray['blocked'])
                if e.lens:
                    self.assertEqual(sum(ev['event']=='Refracción' for ev in ray['events']), 2)

    def test_cap_edge_does_not_hit_fictitious_vertex_mount(self):
        from raytrace import Boundary
        from optics import sag
        b = Boundary(40, -50, 20, 'Concave')
        edge = np.array([40+float(sag(-50, 10)), 10.])
        start = np.array([-120., 0.])
        d = (edge-start)/np.linalg.norm(edge-start)
        hit = b.intersect(start, d)
        self.assertFalse(hit[3])
        np.testing.assert_allclose(hit[1], edge, atol=1e-10)

    def test_full_off_axis_bundles_with_inclusive_edges(self):
        from raytrace import exact_admitted_interval, exact_chief_slope
        from presets import PRESETS
        for name, elements in PRESETS.items():
            boundaries = geometry(elements, 25, 550)
            r = physical_paraxial(elements, 25, 550, -120)
            for height in [0., 5., -5.]:
                interval = exact_admitted_interval(boundaries, -120, height, -300, 400)
                self.assertIsNotNone(interval, (name,height))
                chief = exact_chief_slope(boundaries,r,-120,height,interval,-300,400)
                for slope in list(np.linspace(*interval, 5))+([] if chief is None else [chief]):
                    ray = trace_exact(boundaries,-120,height,math.atan(slope),-300,400)
                    self.assertIsNone(ray['blocked'], (name,height,slope))
                    self.assertAlmostEqual(ray['x'][-1], -300 if r['output_direction']<0 else 400)

    def test_exact_image_comes_from_outgoing_rays(self):
        from raytrace import ray_image
        elements = [Element(index=1.5)]
        boundaries = geometry(elements, 25, 550)
        rays = [trace_exact(boundaries, -120, 0, math.atan(u), -300, 400) for u in [-.03, .03]]
        x, y, rms = ray_image(rays)
        self.assertAlmostEqual(y, 0.)
        self.assertAlmostEqual(rms, 0.)
        for ray in rays:
            q,d = ray['exit_point'],ray['exit_direction']
            self.assertAlmostEqual(q[1]+(x-q[0])*d[1]/d[0], y)
        self.assertGreater(abs(x-physical_paraxial(elements,25,550,-120)['image_x']), .01)

    def test_exact_focus_uses_same_parallel_bundle_as_image(self):
        from raytrace import exact_back_focus, axial_source_bundle, exact_axial_aperture_scale, ray_image
        elements = [Element(index=1.5)]
        r = physical_paraxial(elements,25,550,None)
        bs = geometry(elements,25,550)
        x, seeds = axial_source_bundle(r,'infinity',7,-80)
        h,u = seeds[-1]
        scale = exact_axial_aperture_scale(bs,x,h,u,-300,400)
        image = ray_image([trace_exact(bs,x,y*scale,math.atan(v*scale),-300,400) for y,v in seeds])
        np.testing.assert_allclose(image, exact_back_focus(elements,25,550,7),atol=1e-7)
