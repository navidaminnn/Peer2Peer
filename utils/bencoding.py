from collections import OrderedDict

STR_START = b'0123456789'
INT_START = b'i'
LIST_START = b'l'
DICT_START = b'd'
TYPE_END = b'e'
SIZE_DELIMITER = b':'

class Decoder:
    def __init__(self, value: bytes):
        self.__value = value
        self.__index = 0
        self.__MAX_INDEX = len(value)

    def decode(self):
        '''
        Depending on value's starting byte, return appropriate decoded message
        '''

        # should never reach end of file without decoding ending
        if self.__current_byte() is None:
            raise EOFError("Reached end of error before decoding is completed.")
        
        if self.__current_byte() == INT_START:
            self.__update_index(1)
            return self.__decode_int()
        elif self.__current_byte() == LIST_START:
            return self.__decode_list()
        elif self.__current_byte() == DICT_START:
            return self.__decode_dict()
        elif self.__current_byte() in STR_START:
            return self.__decode_string()
        elif self.__current_byte() == TYPE_END:
            return None

        raise TypeError("Invalid value passed - Value needs to be of type 'bytes'")
    
    def __current_byte(self) -> bytes:
        # use slicing rather than indexing to return byte object rather than int
        if self.__index + 1 >= self.__MAX_INDEX:
            return None
        
        return self.__value[self.__index:self.__index + 1]

    def __update_index(self, increment: int) -> None:
        '''
        Update index of bytes by given param
        '''

        self.__index+= increment

    def __get_size(self) -> int:
        '''
        Determine the size of string/list
        '''

        #TODO: figure out a more 'elegant' approach so we don't have to typecast the slice
        end_index = self.__value.find(SIZE_DELIMITER, self.__index)
        size = int(self.__value[self.__index:end_index])

        return size
    
    def __decode_string(self) -> str:
        str_size = self.__get_size()

        self.__index = self.__value.find(SIZE_DELIMITER, self.__index) + 1
        end_index = self.__index + str_size

        decoded_bytes = self.__value[self.__index:end_index]

        # update index to point at next item
        self.__index = end_index

        return decoded_bytes
    
    def __decode_int(self) -> int:
        # end index is set to next occurance of integer terminator
        end_index = self.__value.find(TYPE_END, self.__index)
        decoded_bytes = self.__value.decode()[self.__index:end_index]

        self.__index = end_index

        #TODO: figure out a more 'elegant' approach so we don't have to typecast
        return int(decoded_bytes)

    def __decode_list(self) -> list:
        list = []
        self.__update_index(1)

        while self.__value[self.__index:self.__index + 1] != TYPE_END:
            list.append(self.decode())

        return list

    def __decode_dict(self) -> dict:
        dict = OrderedDict()
        self.__update_index(1)

        while self.__value[self.__index:self.__index + 1] != TYPE_END:
            key = self.decode()
            value = self.decode()

            dict[key] = value

        return dict

