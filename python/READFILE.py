#encoding:gbk
import pandas as pd
from os.path import isfile


def read_file(filepath, encoding='gbk', sep=None, header=None, names=None, index_col=None,
              usecols=None, squeeze=False, skip_blank_lines=True, **kwargs):
    """
     读取表格类文件数据，默认支持csv,excel(xls),及表格类的txt文件， 返回pandas.DataFrame 或 pandas.Series
    :param filepath: 文件路径
    :type filepath: str
    :param encoding: 文件编码， 默认GBK
    :type encoding: str
    :param sep: 使用的分隔符， csv文件默认为','; txt文件文件默认为tab; excel文件不适用此参数，忽略所传入参数。
    :type sep: str
    :param header: 要用作列名称的行号(0-indexed)
                   如果没有传递names参数，默认为header=0，否则默认header=None。
                   可以是的多索引(multiIndex)的行位置的整数列表，例如[0,1,3]。未指定的中间行将被跳过（例如，在前例中跳过第2行）。
                   如果skip_blank_lines=True，此参数将忽略已注释的行和空行。因此header = 0表示数据的第一行，而不是文件的第一行
    :type header: int or list of int
    :param names: 要使用的列名称列表， 不接受重复项
    :type names: list
    :param index_col: 用作的行标签的列。如果给出序列，则使用多索引 MultiIndex
    :type index_col: int or list of int
    :param usecols: 需要读取的返回列。此数组中的所有元素必须是位置（即，文档列中的整数索引），
                    或对应于用户在名称中提供或从文档标题行推断的列名称的字符串。例如，有效的usecols参数是[0，1，2]或['foo'，'bar'，'baz']；
    :type usecols: list-like
    :param squeeze: 如果解析的数据只包含一列，当squeeze=True时返回一个Series，反之仍然返回DataFrame
    :type squeeze: bool
    :param skip_blank_lines: 如果为True，则跳过文本开头空白行，反之则解析为NaN值。
    :type skip_blank_lines: bool
    :return: 解析结果, 返回为一个pandas.DataFrame对象，或当squeeze=True且结果仅有一列时为pandas.Series对象
    """
    def _check_args(arg, default_val):
        """
        locals() does not check None
        """
        return arg if arg is not None else default_val

    def _pass_to_pd(ftype, filepath, encoding, sep, header, index_col,
                    names, usecols, squeeze, skip_blank_lines, **kwargs):
        """
        passes param to pandas, makes error handling a bit shorter
        """
        try:
            if ftype == 'csv':
                return pd.read_csv(filepath, encoding=encoding, sep=sep, header=header,
                                     index_col=index_col, names=names, usecols=usecols,
                                     squeeze=squeeze, skip_blank_lines=skip_blank_lines, **kwargs)
            elif ftype == 'excel':
                return pd.read_excel(filepath, header=header,
                                       index_col=index_col, names=names, usecols=usecols,
                                       squeeze=squeeze, **kwargs)

            else:
                return pd.read_table(filepath, encoding=encoding, sep=sep, header=header,
                                       index_col=index_col, names=names, usecols=usecols,
                                       squeeze=squeeze, skip_blank_lines=skip_blank_lines, **kwargs)
        except UnicodeDecodeError:
            # GBK Failed, trying UTF
            return _pass_to_pd(ftype, filepath, 'utf-8', sep, header, index_col, names,
                               usecols, squeeze, skip_blank_lines, **kwargs)

    # test whether the file is readable and iterable
    if not isfile(filepath):
        raise ValueError('文件不存在或不可读')

    if filepath.endswith('csv'):
        sep = _check_args(sep, ',')
        header = _check_args(header, 'infer')
        result = _pass_to_pd('csv', filepath, encoding, sep, header, index_col, names,
                             usecols, squeeze, skip_blank_lines, **kwargs)
    elif filepath.endswith('xls'):
        if sep is not None:
            SyntaxWarning('Excel 文件默认不使用分隔符，忽略传入sep参数')
        elif encoding is not None:
            SyntaxWarning('Excel 文件读取不支持编码参数')
        elif skip_blank_lines is not None:
            SyntaxWarning('Excel 文件读取不支持skip_blank_lines参数')

        header = _check_args(header, 0)
        result = _pass_to_pd('excel', filepath, encoding, sep, header, index_col, names,
                             usecols, squeeze, skip_blank_lines, **kwargs)
    elif filepath.endswith('txt'):
        sep = _check_args(sep, '\t')
        header = _check_args(header, 'infer')
        result = _pass_to_pd('txt', filepath, encoding, sep, header, index_col, names,
                             usecols, squeeze, skip_blank_lines, **kwargs)

    elif filepath.endswith('xlsx'):
        raise ValueError('暂时不支持解析xlsx文件，请使用xls')
    else:
        raise ValueError('不支持的文件类型')
    return result

