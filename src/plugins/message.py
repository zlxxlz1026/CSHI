

class Message():
    '''
    Reference: https://github.com/zhayujie/chatgpt-on-wechat/blob/master/bridge/context.py
    '''
    def __init__(self, content, message_type, **kwargs):
        # content 为消息内容，message_type 为消息类型，kwargs 为不同插件的memory输出
        self.content = content
        self.message_type = message_type
        self.kwargs = kwargs
    
    def __contains__(self, key):
        if key == "type":
            return self.message_type is not None
        elif key == "content":
            return self.content is not None
        else:
            return key in self.kwargs
    
    def __getitem__(self, key):
        if key == "type":
            return self.message_type
        elif key == "content":
            return self.content
        else:
            return self.kwargs[key]
        
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
    
    def __setitem__(self, key, value):
        if key == "type":
            self.message_type = value
        elif key == "content":
            self.content = value
        else:
            self.kwargs[key] = value
            
    def __delitem__(self, key):
        if key == "type":
            self.message_type = None
        elif key == "content":
            self.content = None
        else:
            del self.kwargs[key]
            
    def __str__(self):
        return "Message(type={}, content={}, kwargs={})".format(self.message_type, self.content, self.kwargs)