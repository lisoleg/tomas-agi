"""EML 数学降维工具箱单元测试"""
import sys
import os
import pytest
import json

# Add sim/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sim'))

from eml_dimred.hyperedge import HypEdge, EMLVertex, load_eml_graph
from eml_dimred.matroid import Matroid, matroid_prune
from eml_dimred.gpct import GpctDecomposer, gpct_decompose
from eml_dimred.itc import ItcAnneal, itc_anneal
from eml_dimred.brown_miklos import BrownMiklosCompressor, brown_miklos_compress
from eml_dimred.pipeline import slim_eml, DimredResult


# ─── Test Data ───

@pytest.fixture
def sample_edges():
    """Create sample hyperedges for testing"""
    return [
        HypEdge(nodes=(0, 1), eid='e0', i_val=0.95, asym=0.0),
        HypEdge(nodes=(1, 2), eid='e1', i_val=0.85, asym=0.0),
        HypEdge(nodes=(0, 2), eid='e2', i_val=0.60, asym=0.0),
        HypEdge(nodes=(2, 3), eid='e3', i_val=0.45, asym=0.0),
        HypEdge(nodes=(3, 4), eid='e4', i_val=0.15, asym=0.0),
        HypEdge(nodes=(0, 3), eid='e5', i_val=0.10, asym=0.0),
        HypEdge(nodes=(0, 1), eid='e6', i_val=0.70, asym=0.5),  # MUS-capable
    ]


@pytest.fixture
def sample_vertices():
    """Create sample vertices"""
    return [
        EMLVertex(vid=0, concept='概念A', i_val=0.9),
        EMLVertex(vid=1, concept='概念B', i_val=0.8),
        EMLVertex(vid=2, concept='概念C', i_val=0.5),
        EMLVertex(vid=3, concept='概念D', i_val=0.3),
        EMLVertex(vid=4, concept='概念E', i_val=0.1),
    ]


# ─── HypEdge Tests ───

class TestHypEdge:
    def test_arity(self):
        e = HypEdge(nodes=(0, 1, 2), eid='e1', i_val=0.5)
        assert e.arity == 3

    def test_is_mus_capable(self):
        boolean_edge = HypEdge(nodes=(0, 1), eid='e1', i_val=0.5, asym=0.0)
        mus_edge = HypEdge(nodes=(0, 1), eid='e2', i_val=0.5, asym=0.5)

        assert not boolean_edge.is_mus_capable
        assert mus_edge.is_mus_capable

    def test_is_alive(self):
        alive = HypEdge(nodes=(0,), eid='e1', i_val=0.5)
        dead = HypEdge(nodes=(0,), eid='e2', i_val=0.05)

        assert alive.is_alive(0.15)
        assert not dead.is_alive(0.15)

    def test_i_val_clamped(self):
        e = HypEdge(nodes=(0,), eid='e1', i_val=1.5)
        assert e.i_val == 1.0
        e2 = HypEdge(nodes=(0,), eid='e2', i_val=-0.5)
        assert e2.i_val == 0.0


# ─── Matroid Tests ───

class TestMatroid:
    def test_find_base(self, sample_edges):
        m = Matroid(sample_edges)
        base = m.find_base(dead_threshold=0.15)

        # Should exclude dead edges (e4: 0.10, e5: 0.10)
        assert len(base) >= 4
        assert all(e.is_alive(0.15) for e in base)

    def test_find_base_mus(self, sample_edges):
        """Test that MUS-capable edges are handled differently"""
        m = Matroid(sample_edges)
        base = m.find_base(dead_threshold=0.15)

        # MUS edge e6 (0.70) should be kept even though it shares nodes with e0
        mus_edges = [e for e in base if e.is_mus_capable]
        assert len(mus_edges) >= 1

    def test_get_rank(self, sample_edges):
        m = Matroid(sample_edges)
        rank = m.get_rank()
        assert rank > 0

    def test_matroid_prune(self, sample_edges, sample_vertices):
        pruned, stats = matroid_prune(sample_edges, sample_vertices)
        assert len(pruned) <= len(sample_edges)
        assert stats['compression_ratio'] > 0
        assert 'mus_circuits' in stats
        assert 'paradox_circuits' in stats


# ─── GPCT Tests ───

class TestGPCT:
    def test_decompose(self, sample_edges, sample_vertices):
        decomp, result = gpct_decompose(sample_edges, sample_vertices, k=2)

        assert decomp.k == 2
        assert len(decomp.boundary_layer) == 2
        assert len(decomp.outer_region) >= 2
        assert result['is_fpt']  # k=2 is always FPT

    def test_complexity_estimate(self, sample_edges):
        decomp = GpctDecomposer(sample_edges, k=3)
        est = decomp.estimate_complexity()
        assert est['complexity_class'] == 'FPT'
        assert est['feasible']

    def test_coupling_map(self, sample_edges):
        decomp = GpctDecomposer(sample_edges, k=3)
        rho = decomp.coupling_map
        assert len(rho) > 0
        # High-degree nodes should have higher coupling
        assert rho[0] > 0  # Node 0 participates in multiple edges


# ─── ITC Tests ───

class TestITC:
    def test_anneal(self, sample_edges):
        best_set, remaining, stats = itc_anneal(
            sample_edges, tau_max=100, verbose=False
        )
        assert len(best_set) > 0
        assert stats['steps'] <= 100
        assert 'best_i' in stats

    def test_identify_bl(self, sample_edges, sample_vertices):
        annealer = ItcAnneal(sample_edges, sample_vertices)
        bl = annealer.identify_boundary_layer(k=2)
        assert len(bl) == 2
        # High-coupling nodes should be in BL
        assert 0 in bl  # Node 0 has highest degree


# ─── Brown-Miklós Tests ───

class TestBrownMiklos:
    def test_compress(self, sample_edges):
        bm, stats = brown_miklos_compress(sample_edges, t=2)
        assert bm.k > 0
        assert stats['is_fpt']
        assert stats['k'] > 0

    def test_is_fpt(self, sample_edges):
        bm = BrownMiklosCompressor(sample_edges, t=2)
        assert bm.is_fpt(max_k=50)

    def test_degree_classes(self, sample_edges):
        bm = BrownMiklosCompressor(sample_edges)
        compressed = bm.get_compressed_representation()
        assert len(compressed) == bm.k


# ─── Pipeline Tests ───

class TestPipeline:
    def test_slim_eml(self, sample_edges, sample_vertices):
        result = slim_eml(
            edges=sample_edges,
            vertices=sample_vertices,
            kappa=4.0,
            tau_max=50,
            skip_strf=True,
            verbose=False,
        )
        assert isinstance(result, DimredResult)
        assert result.original_edges == len(sample_edges)
        assert len(result.core_edges) > 0
        assert result.compression_ratio >= 0
        assert result.is_fpt

    def test_predictions(self, sample_edges, sample_vertices):
        result = slim_eml(
            edges=sample_edges,
            vertices=sample_vertices,
            tau_max=50,
            verbose=False,
        )
        assert 'P_DimRed_1' in result.predictions
        assert 'P_DimRed_2' in result.predictions
        assert 'P_DimRed_3' in result.predictions


# ─── EML File Loading Tests ───

class TestEMLLoading:
    def test_load_physics_eml(self):
        eml_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'physics_distilled.eml'
        )
        concepts_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'physics_distilled.concepts.json'
        )

        if not os.path.exists(eml_path):
            pytest.skip("physics_distilled.eml not found")

        vertices, edges, metadata = load_eml_graph(eml_path, concepts_path)
        assert metadata['num_vertices'] > 0
        assert metadata['num_edges'] > 0
        assert len(vertices) == metadata['num_vertices']
        assert len(edges) == metadata['num_edges']

    def test_slim_eml_on_real_data(self):
        eml_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'physics_distilled.eml'
        )
        concepts_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'physics_distilled.concepts.json'
        )

        if not os.path.exists(eml_path):
            pytest.skip("physics_distilled.eml not found")

        vertices, edges, _ = load_eml_graph(eml_path, concepts_path)
        result = slim_eml(edges=edges, vertices=vertices, tau_max=50, verbose=False)

        assert result.is_fpt
        assert result.compression_ratio >= 0
        assert result.i_retention > 0.5  # Should retain most I
