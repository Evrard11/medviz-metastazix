import pickle

def load_model(path):
    with open(path, 'rb') as f:
        modele = pickle.load(f)
    return modele