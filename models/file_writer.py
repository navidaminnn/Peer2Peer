from metainfo import MetaInfo
from models.piece_status import PieceStatus
import os

class FileWriter:
    def __init__(self, meta_info: MetaInfo, piece_status: PieceStatus):
        self.meta_info = meta_info
        self.piece_status = piece_status

        self.pieces = self.piece_status.pieces

        self.length = meta_info.length
        self.multi_files = meta_info.multi_files

        self.file_lengths = self.__get_file_lengths()
        self.file_path = self.__get_path()

    def write(self, piece_index: int, piece_byte_offset: int, data: bytes):
        total_offset = 0

        for i in range(piece_index):
            total_offset += self.pieces[i].length

        total_offset += piece_byte_offset

        if not self.multi_files:
            with open(self.file_path, 'wb') as f:
                print(len(data))
                f.seek(total_offset)
                f.write(data)
        else:
            file_len = 0

            for i in range(self.file_lengths):
                if file_len + self.file_lengths[i] > total_offset:
                    break

                file_len += self.file_lengths[i]

            # write data to file at file_offset
            file_offset = total_offset - file_len

    def __get_file_lengths(self) -> list | None:
        if self.multi_files:
            file_lengths = [file['length'] for file in self.meta_info.files]
            return file_lengths
        
        return None
    
    def __get_path(self):
        if self.multi_files:
            pass

        return os.path.join('downloads/' + self.meta_info.name)
    os.getcwd()