from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from nber_cli.citation import FORMATS, format_citation
from nber_cli.clipboard import ClipboardError, copy_text
from nber_cli.cli import main
from nber_cli.core.models import NBER


@pytest.fixture
def paper():
    return NBER(1234, 'Trade & Growth', ['Laura Alfaro', 'Pol Antràs', 'Davin Chor'], '2026-07-13', '')


def test_bibtex_escaping_and_stable_key(paper):
    paper.title = r'A & B: 50% of {GDP}_$# \\ ~ ^'
    result = format_citation(paper)
    assert result.startswith('@techreport{nberw1234,')
    assert r'50\% of \{GDP\}\_\$\#' in result
    assert r'\textbackslash{}' in result
    assert 'Alfaro, Laura and Antràs, Pol and Chor, Davin' in result
    assert 'number = {1234}' in result


@pytest.mark.parametrize('style', FORMATS)
def test_all_formats_are_plain_text(paper, style):
    result = format_citation(paper, style, accessed=date(2026, 11, 9))
    assert 'National Bureau of Economic Research' in result
    assert 'https://www.nber.org/papers/w1234' in result
    assert '**' not in result


def test_author_rules(paper):
    paper.authors = ['Ludwig van Beethoven', 'Antràs, Pol']
    assert format_citation(paper, 'apa').startswith('van Beethoven, L. & Antràs, P. (2026).')
    assert format_citation(paper, 'mla').startswith('van Beethoven, Ludwig, and Pol Antràs.')
    paper.authors += ['Davin Chor']
    assert ', et al.' in format_citation(paper, 'mla')
    assert 'VAN BEETHOVEN L, ANTRÀS P, CHOR D.' in format_citation(paper, 'gb')
    paper.authors += ['Fourth Author']
    assert ', et al.' in format_citation(paper, 'gb')


def test_missing_metadata(paper):
    paper.authors = []
    paper.date = ''
    assert 'year =' not in format_citation(paper)
    assert 'author =' not in format_citation(paper)
    assert 'Unknown author (n.d.).' in format_citation(paper, 'apa')
    assert '[2026-11-09]' in format_citation(paper, 'gb', accessed=date(2026, 11, 9))


def test_apa_long_author_list(paper):
    paper.authors = [f'Given Family{i}' for i in range(21)]
    result = format_citation(paper, 'apa')
    assert 'Family18, G., … Family20, G.' in result
    assert 'Family19' not in result


@pytest.mark.parametrize('options', [[], ['-f', 'apa'], ['--format', 'gbt7714'], ['--stdout', '--refresh']])
def test_cite_dispatch(paper, options, capsys):
    fetch = AsyncMock(return_value=SimpleNamespace(paper=paper))
    with patch('sys.argv', ['nber-cli', 'cite', 'W01234', *options]), patch('nber_cli.cli.get_paper_with_info_cache_result', fetch), patch('nber_cli.cli.copy_text') as copy:
        main()
    fetch.assert_awaited_once_with(1234, refresh='--refresh' in options)
    out = capsys.readouterr()
    if '--stdout' in options:
        copy.assert_not_called()
        assert out.out.startswith('@techreport')
        assert out.err == ''
    else:
        copy.assert_called_once()
        assert out.out == ''
        assert 'Copied' in out.err


def test_clipboard_failure_preserves_citation(paper, capsys):
    with patch('sys.argv', ['nber-cli', 'cite', 'w1234']), patch('nber_cli.cli.get_paper_with_info_cache_result', AsyncMock(return_value=SimpleNamespace(paper=paper))), patch('nber_cli.cli.copy_text', side_effect=ClipboardError('Unavailable')):
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 1
    out = capsys.readouterr()
    assert out.out == format_citation(paper) + '\n'
    assert 'Could not copy' in out.err
    assert 'Copied' not in out.err


@pytest.mark.parametrize('args', [['w0'], ['bogus'], ['w1234', '-f', 'invalid']])
def test_invalid_input_does_not_fetch(args):
    with patch('sys.argv', ['nber-cli', 'cite', *args]), patch('nber_cli.cli.get_paper_with_info_cache_result') as fetch:
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 2
    fetch.assert_not_called()


def test_network_failure_does_not_copy(capsys):
    with patch('sys.argv', ['nber-cli', 'cite', 'w1234']), patch('nber_cli.cli.get_paper_with_info_cache_result', AsyncMock(side_effect=TimeoutError)), patch('nber_cli.cli.copy_text') as copy:
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 1
    copy.assert_not_called()
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('platform,env,expected', [('darwin', {}, 'pbcopy'), ('win32', {}, 'powershell.exe'), ('linux', {'WAYLAND_DISPLAY': 'wayland-0'}, 'wl-copy'), ('linux', {'DISPLAY': ':0'}, 'xclip')])
def test_native_clipboard(platform, env, expected):
    with patch('nber_cli.clipboard.sys.platform', platform), patch.dict('os.environ', env, clear=True), patch('nber_cli.clipboard.shutil.which', return_value='/bin/tool'), patch('nber_cli.clipboard.subprocess.run') as run:
        copy_text('Antràs 中文')
    assert run.call_args.args[0][0] == expected
    assert run.call_args.kwargs['input'] == 'Antràs 中文'.encode()
    assert run.call_args.kwargs['check'] is True


def test_clipboard_fallback():
    with patch('nber_cli.clipboard.sys.platform', 'linux'), patch.dict('os.environ', {'WAYLAND_DISPLAY': 'wayland-0', 'DISPLAY': ':0'}, clear=True), patch('nber_cli.clipboard.shutil.which', return_value='/bin/tool'), patch('nber_cli.clipboard.subprocess.run', side_effect=[OSError(), None]) as run:
        copy_text('citation')
    assert run.call_args.args[0][0] == 'xclip'


def test_headless_clipboard():
    with patch('nber_cli.clipboard.sys.platform', 'linux'), patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ClipboardError):
            copy_text('citation')


def test_cite_reuses_info_cache_and_refreshes(paper, capsys):
    from nber_cli import config_store, db

    config_store.set_info_cache_enabled(True)
    db.init_database(None)
    db.write_info_cache(None, paper)
    remote = AsyncMock(return_value=NBER(1234, 'Updated title', paper.authors, paper.date, ''))
    with patch('nber_cli.db.info_cache.get_nber', remote):
        with patch('sys.argv', ['nber-cli', 'cite', 'w1234', '--stdout']):
            main()
        assert r'Trade \& Growth' in capsys.readouterr().out
        remote.assert_not_awaited()
        with patch('sys.argv', ['nber-cli', 'cite', 'w1234', '--stdout', '--refresh']):
            main()
        assert 'Updated title' in capsys.readouterr().out
        remote.assert_awaited_once_with(1234)
    assert db.read_info_cache(None, 1234).title == 'Updated title'
