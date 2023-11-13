def get_first_last_name(full_name):
    if len(full_name.split(' ')) == 2:
        return full_name.split(' ')
    return '', ''
