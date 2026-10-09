import zstandard

from scripts.load_games import open_pgn

SAMPLE = '[Event "x"]\n\n1. e4 *\n'


def test_open_pgn_reads_zst(tmp_path):
    path = tmp_path / "sample.pgn.zst"
    path.write_bytes(zstandard.ZstdCompressor().compress(SAMPLE.encode("utf-8")))
    with open_pgn(path) as handle:
        assert handle.read() == SAMPLE

def test_open_pgn_reads_plain_text(tmp_path):
    path = tmp_path / "sample.pgn"
    path.write_text(SAMPLE, encoding="utf-8")
    with open_pgn(path) as handle:
        assert handle.read() == SAMPLE