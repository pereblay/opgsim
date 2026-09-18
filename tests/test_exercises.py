import copy
import unittest
from exercises import generate_exercise, assess_exercise, public_exercise


def solved(ex):
    return dict(placements={'object':[ex['object_x'],0], **{e['name']:[e['position'],0] for e in ex['elements']}},
                rays=[dict(id=r['id'],points=copy.deepcopy(r['points'])) for r in ex['rays']],draft=[])


class ExerciseTests(unittest.TestCase):
    def test_random_exercises_are_solvable_and_reproducible(self):
        for count in [1,2,3]:
            for seed in range(20):
                ex=generate_exercise(count, seed)
                self.assertEqual(len(ex['elements']),count)
                self.assertLessEqual(sum(e['kind'].startswith('Espejo') for e in ex['elements']),1)
                self.assertTrue(assess_exercise(ex,solved(ex))['correct'], (count,seed))
                self.assertTrue(all(e['kind']!='Diafragma' for e in ex['elements']))
        self.assertEqual(generate_exercise(3,42),generate_exercise(3,42))

    def test_wrong_placement_and_missing_rays(self):
        ex=generate_exercise(1,123)
        self.assertFalse(assess_exercise(ex,{})['correct'])
        scene=solved(ex);scene['placements']['object'][0]+=20
        self.assertTrue(any('posición incorrecta' in m for m in assess_exercise(ex,scene)['issues']))

    def test_wrong_intersection_and_reflection_detected(self):
        ex=generate_exercise(1,123)  # Plane mirror
        scene=solved(ex);scene['rays'][0]['points'][1][0]+=20
        self.assertTrue(any('superficie' in m for m in assess_exercise(ex,scene)['issues']))
        scene=solved(ex);p=scene['rays'][0]['points']
        p[-1]=[p[-2][0]+100,p[-2][1]]
        report=assess_exercise(ex,scene)
        self.assertFalse(report['correct'])
        self.assertTrue(any('reflexión' in m for m in report['issues']))

    def test_endpoint_can_be_anywhere_on_outgoing_ray(self):
        ex=generate_exercise(2,123);scene=solved(ex)
        for ray in scene['rays']:
            a,b=ray['points'][-2:]
            ray['points'][-1]=[a[i]+.5*(b[i]-a[i]) for i in range(2)]
        self.assertTrue(assess_exercise(ex,scene)['correct'])

    def test_no_solution_in_canvas_payload_and_malformed_submission(self):
        ex=generate_exercise(1,123)
        self.assertTrue(all(set(r)=={'id','label'} for r in public_exercise(ex)['rays']))
        for scene in [None,{},dict(placements={'object':[float('nan'),0]},rays=[]),dict(placements=[],rays=3)]:
            self.assertFalse(assess_exercise(ex,scene)['correct'])

    def test_invalid_count(self):
        for count in [0,4,-1]:
            with self.assertRaises(ValueError):generate_exercise(count,1)

    def test_chief_and_marginals_have_distinct_origins(self):
        for n in [1,2,3]:
            ex=generate_exercise(n,42)
            chief,upper,lower=ex['rays']
            self.assertEqual(chief['points'][0][1],ex['object_height'])
            for marginal in [upper,lower]:
                self.assertEqual(marginal['points'][0][1],0.)
                self.assertGreater(len(marginal['points']),2)
            name=ex['stop']['name'].replace(' · retorno','')
            indices=[i+1 for i,s in enumerate(chief['surfaces']) if s==name]
            index=indices[-1] if 'retorno' in ex['stop']['name'] else indices[0]
            self.assertAlmostEqual(chief['points'][index][1],0.,places=6)
            auxiliary=generate_exercise(n,42,'construction')
            self.assertIn('Paralelo',auxiliary['rays'][0]['label'])
            self.assertTrue(assess_exercise(auxiliary,solved(auxiliary))['correct'])
