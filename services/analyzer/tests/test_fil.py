from services.analyzer.filter import mark_developer_focus

def test_keyword_positive():
    assert mark_developer_focus("AI breakthrough", "some developer programming content")

def test_keyword_negative():
    assert not mark_developer_focus("Gardening tips", "Learn to plant roses")

def test_embedding_positive():
    # A semantically close phrase to "machine learning" should pass
    text = "This article discusses neural networks and deep learning architectures."
    assert mark_developer_focus("", text)
