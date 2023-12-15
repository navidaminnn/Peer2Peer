import utils.bencoding as bencoding

if __name__ == "__main__":
    var = bytes(b'127389:Middle Earth')
    decoded_var = bencoding.Decoder(var).decode()

    print(decoded_var)
    print(type(decoded_var))
