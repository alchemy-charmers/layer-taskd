import imp
import mock


class TestActions():
    def test_add_key(self, taskd, monkeypatch):
        mock_function = mock.Mock()
        monkeypatch.setattr(taskd, 'add_key', mock_function)
        assert mock_function.call_count == 0
        imp.load_source('add_key', './actions/add-key')
        assert mock_function.call_count == 1

    def test_del_key(self, taskd, monkeypatch):
        mock_function = mock.Mock()
        monkeypatch.setattr(taskd, 'del_key', mock_function)
        assert mock_function.call_count == 0
        imp.load_source('del_key', './actions/del-key')
        assert mock_function.call_count == 1

    def test_list_keys(self, taskd, monkeypatch):
        mock_function = mock.Mock()
        monkeypatch.setattr(taskd, 'list_keys', mock_function)
        assert mock_function.call_count == 0
        imp.load_source('list_keys',
                        './actions/list-keys')
        assert mock_function.call_count == 1
