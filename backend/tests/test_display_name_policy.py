"""Chi si registra sceglie come farsi chiamare — entro certi limiti.

Due lati, ugualmente importanti: i nomi che vanno respinti e i nomi normali che
devono continuare a passare. Un filtro che blocca "Cassandra" o il cognome
"Negro" fa più danni di quanti ne eviti, quindi i falsi positivi sono testati
quanto i veri positivi.
"""

import pytest

from app.services.display_name_policy import DisplayNameRejected, check, normalise


@pytest.mark.parametrize(
    "name",
    [
        "Sergio",
        "Anna Rossi",
        "Jean-Luc",
        "Traceur_92",
        "Marco88",
        "J. R. R. Tolkien",
        "Ali",
        "María José",
        "Владимир",
        "苏州 Traceur",
    ],
)
def test_ordinary_names_are_accepted(name: str) -> None:
    assert check(name)


@pytest.mark.parametrize(
    "name",
    [
        "Cassandra",  # contiene "ass"
        "Scunthorpe",  # il caso di scuola dei filtri
        "Analisa",
        "Negro",  # cognome italiano e spagnolo
        "Negroni",
        "Montenegro",
        "Gay Pride Roma",
        "Gaylord Focker",
    ],
)
def test_innocent_names_that_trip_naive_filters_are_accepted(name: str) -> None:
    assert check(name)


@pytest.mark.parametrize(
    "name",
    [
        "nigger",
        "frocio",
        "F.R.O.C.I.O",
        "n3gr0",
        "N.E.G.R.O",
    ],
)
def test_slurs_are_refused_however_they_are_written(name: str) -> None:
    with pytest.raises(DisplayNameRejected):
        check(name)


@pytest.mark.parametrize(
    "name",
    ["HeilHitler", "sieg heil", "white power", "1488 boy", "kkk", "morte agli ebrei"],
)
def test_hate_calls_are_refused(name: str) -> None:
    with pytest.raises(DisplayNameRejected):
        check(name)


@pytest.mark.parametrize("name", ["admin", "Moderatore", "PkFamily Staff", "root"])
def test_impersonating_the_staff_is_refused(name: str) -> None:
    with pytest.raises(DisplayNameRejected):
        check(name)


@pytest.mark.parametrize("name", ["stronzo", "puttana", "Fuck", "bitch"])
def test_plain_insults_are_refused(name: str) -> None:
    with pytest.raises(DisplayNameRejected):
        check(name)


@pytest.mark.parametrize("name", ["a", "  ", "!!!", "x" * 81])
def test_names_that_are_not_names_are_refused(name: str) -> None:
    with pytest.raises(DisplayNameRejected):
        check(name)


def test_the_accepted_name_comes_back_tidy() -> None:
    assert check("  Anna   Rossi  ") == "Anna Rossi"


def test_normalise_folds_accents_leet_and_punctuation() -> None:
    assert normalise("Mà.rc0_88") == "marcobb"
    assert normalise("N3GR0") == "negro"


def test_the_message_says_what_is_wrong_without_repeating_it() -> None:
    with pytest.raises(DisplayNameRejected) as rejected:
        check("HeilHitler")

    message = str(rejected.value)
    assert "hatred" in message
    assert "hitler" not in message.lower()
