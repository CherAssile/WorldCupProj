from app.services import elo


def test_equal_ratings_give_fifty_fifty_expected_score() -> None:
    assert elo.expected_score(1500, 1500) == 0.5


def test_higher_rated_team_has_higher_expected_score() -> None:
    assert elo.expected_score(1700, 1500) > 0.5
    assert elo.expected_score(1500, 1700) < 0.5


def test_actual_score_win_draw_loss() -> None:
    assert elo.actual_score(2, 0) == 1.0
    assert elo.actual_score(1, 1) == 0.5
    assert elo.actual_score(0, 2) == 0.0


def test_k_factor_tiers_friendly_lowest_world_cup_highest() -> None:
    assert elo.k_factor("Friendly") == elo.K_FRIENDLY
    assert elo.k_factor("FIFA World Cup") == elo.K_WORLD_CUP
    assert elo.k_factor("UEFA Euro qualification") == elo.K_OFFICIAL
    assert elo.K_FRIENDLY < elo.K_OFFICIAL < elo.K_WORLD_CUP


def test_win_increases_winner_rating_and_decreases_losers() -> None:
    new_home, new_away = elo.update_ratings(1500, 1500, 2, 0, "Friendly")
    assert new_home > 1500
    assert new_away < 1500


def test_draw_between_equal_ratings_leaves_them_unchanged() -> None:
    new_home, new_away = elo.update_ratings(1500, 1500, 1, 1, "Friendly")
    assert new_home == 1500
    assert new_away == 1500


def test_update_is_always_zero_sum() -> None:
    """Ce que l'une gagne, l'autre le perd exactement : propriété de base d'un Elo."""
    new_home, new_away = elo.update_ratings(1620, 1480, 1, 3, "FIFA World Cup")
    assert (new_home - 1620) == -(new_away - 1480)


def test_upset_win_gains_more_than_expected_win() -> None:
    """Une victoire surprise (négatif battant un favori) rapporte plus de points qu'une
    victoire attendue (favori qui gagne), à K égal."""
    upset_gain = elo.update_ratings(1400, 1700, 1, 0, "Friendly")[0] - 1400
    expected_win_gain = elo.update_ratings(1700, 1400, 1, 0, "Friendly")[0] - 1700
    assert upset_gain > expected_win_gain


def test_world_cup_result_moves_rating_more_than_a_friendly() -> None:
    """Même résultat, même écart de niveau, mais enjeu différent : la Coupe du monde
    bouge davantage la note (K plus élevé)."""
    friendly_gain = elo.update_ratings(1500, 1500, 1, 0, "Friendly")[0] - 1500
    world_cup_gain = elo.update_ratings(1500, 1500, 1, 0, "FIFA World Cup")[0] - 1500
    assert world_cup_gain > friendly_gain
