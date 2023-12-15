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

        # 'base case' - no more calls needed once index is max'd
        if self.__index == self.__MAX_INDEX:
            print("This is done")
            return

        # use slicing rather than indexing to return byte object rather than int
        if self.__value[self.__index:self.__index + 1] == INT_START:
            self.__update_index(1)
            return self.__decode_int()
        elif self.__value[self.__index:self.__index + 1] == LIST_START:
            return self.__decode_list()
        elif self.__value[self.__index:self.__index + 1] == DICT_START:
            return self.decode_dict()
        elif self.__value[self.__index:self.__index + 1] in STR_START:
            return self.__decode_string()

        raise TypeError("Invalid value passed - Value needs to be of type 'bytes'")

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

        #TODO: either utilize update_index func. or remove it altogether
        self.__index = self.__value.find(SIZE_DELIMITER, self.__index) + 1
        end_index = self.__index + str_size

        decoded_bytes = self.__value[self.__index:end_index]

        return decoded_bytes
    
    def __decode_int(self) -> int:
        # end index is set to next occurance of integer terminator
        end_index = self.__value.find(TYPE_END, self.__index)
        decoded_bytes = self.__value.decode()[self.__index:end_index]

        self.__index = end_index

        return int(decoded_bytes)

    def __decode_list(self) -> list:
        list = []
        list_size = self.__get_size()

        #TODO: either utilize update_index func. or remove it altogether
        self.__index = self.__value.find(SIZE_DELIMITER, self.__index) + 1

        for i in range(list_size):
            
            pass

        return list

    def decode_dict(self) -> dict:
        pass