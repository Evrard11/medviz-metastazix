import pickle

def load_model(path):
    with open(path, 'rb') as f:
        modele = pickle.load(f)
    return modele

def save_model(model, path):
    with open(path, 'wb') as f:
        pickle.dump(model, f)
