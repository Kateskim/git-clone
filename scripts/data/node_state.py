import maya.cmds as cmds
import maya.OpenMaya as om

import numpy as np

try:
    from scipy.spatial import cKDTree as kd_tree
except ImportError:
    from scipy.spatial import cKDTree as kd_tree

import node_utils
import window_utils


class SporeState(object):
    def __init__(self, node):

        dag_fn = om.MFnDagNode(node)
        self.node_name = dag_fn.fullPathName()
        self.node = node
        self.state = None
        self.data_plug = om.MPlug()
        self.data_object = om.MObject()

        self.position = om.MVectorArray()
        self.scale = om.MVectorArray()
        self.rotation = om.MVectorArray()
        self.instance_id = om.MIntArray()
        self.visibility = om.MIntArray()

        self.normal = om.MVectorArray()
        self.tangent = om.MVectorArray()
        self.u_coord = om.MDoubleArray()
        self.v_coord = om.MDoubleArray()
        self.poly_id = om.MIntArray()
        self.color = om.MVectorArray()
        self.unique_id = om.MIntArray()

        self.exclusive_paint = []
        self.bounding_box = dag_fn.boundingBox()

        self.np_position = np.empty((0,3), float)
        self.tree = None

        self.initialize_cache()

    def initialize_cache(self):
        """ get cache data from the sporeNode's instanceData plug/
        :param instance_data_plug MPlug: instanceData plug """

        node_fn = om.MFnDependencyNode(self.node)
        self.data_plug = node_fn.findPlug('instanceData')
        self.data_object = self.data_plug.asMObject()
        array_attr_fn = om.MFnArrayAttrsData(self.data_object)

        self.position = array_attr_fn.vectorArray('position')
        self.scale = array_attr_fn.vectorArray('scale')
        self.rotation = array_attr_fn.vectorArray('rotation')
        self.instance_id = array_attr_fn.intArray('objectIndex')
        self.visibility = array_attr_fn.intArray('visibility')
        self.normal = array_attr_fn.vectorArray('normal')
        self.tangent = array_attr_fn.vectorArray('tangent')
        self.u_coord = array_attr_fn.doubleArray('u_coord')
        self.v_coord = array_attr_fn.doubleArray('v_coord')
        self.poly_id = array_attr_fn.intArray('poly_id')
        self.color = array_attr_fn.vectorArray('color')
        self.unique_id = array_attr_fn.intArray('unique_id')

        # TODO - set bb

        # get position as numpy array
        for i in xrange(self.position.length()):
            position = [[self.position[i].x, self.position[i].y, self.position[i].z]]
            self.np_position = np.append(self.np_position, position, axis=0)
        #  print 'init np arrat:', self.np_position


    def get_node_state(self):
        """ fetch brush setting from the node and save it to the "state" dict """

        # get selected item from node's textScrollList
        sel = cmds.textScrollList('instanceList', q=True, si=True)
        if sel:
            object_index = [int(s.split(' ')[0].strip('[]:')) for s in sel]
        else:
            elements = cmds.textScrollList('instanceList', q=True, ai=True)
            object_index = [int(e.split(' ')[0].strip('[]:')) for e in elements]

        # get modes
        modes = ['place', 'spray', 'scale', 'align', 'move', 'id', 'remove']
        mode_id = cmds.getAttr('{}.contextMode'.format(self.node_name))
        align_modes = ['normal', 'world', 'object', 'stroke']
        align_id = cmds.getAttr('{}.alignTo'.format(self.node_name))

        # save state
        self.state = {'mode': modes[mode_id],
                      'num_samples': cmds.getAttr('{}.numBrushSamples'.format(self.node_name)),
                      'min_distance': cmds.getAttr('{}.minDistance'.format(self.node_name)),
                      'fall_off': cmds.getAttr('{}.fallOff'.format(self.node_name)),
                      'align_to': align_modes[align_id],
                      'strength': cmds.getAttr('{}.strength'.format(self.node_name)),
                      'min_rot': cmds.getAttr('{}.minRotation'.format(self.node_name))[0],
                      'max_rot': cmds.getAttr('{}.maxRotation'.format(self.node_name))[0],
                      'uni_scale': cmds.getAttr('{}.uniformScale'.format(self.node_name)),
                      'min_scale': cmds.getAttr('{}.minScale'.format(self.node_name))[0],
                      'max_scale': cmds.getAttr('{}.maxScale'.format(self.node_name))[0],
                      'scale_factor': cmds.getAttr('{}.scaleFactor'.format(self.node_name)),
                      'scale_amount': cmds.getAttr('{}.scaleAmount'.format(self.node_name)),
                      'min_offset': cmds.getAttr('{}.minOffset'.format(self.node_name)),
                      'max_offset': cmds.getAttr('{}.maxOffset'.format(self.node_name)),
                      'ids': object_index}


    def build_kd_tree(self, refresh_position=False):
        """ build the kd tree """

        if refresh_position:
            self.np_position = np.empty((0, 3), float)
            for i in xrange(self.position.length()):
                position = [[self.position[i].x, self.position[i].y, self.position[i].z]]
                self.np_position = np.append(self.np_position, position, axis=0)

        self.tree = kd_tree(self.np_position)

    def set_state(self):
        """ set the currently cached point data as node instanceData attribute
        and refresh the view to make changes visible """

        self.data_plug.setMObject(self.data_object)
        view = window_utils.active_view()
        view.refresh(True, False)

    def get_data_object(self):
        """ return the mObject containing instanceData attribute
        :return mObject: """

        return self.data_object


    def append_points(self, position, scale, rotation, instance_id, visibility, normal, tangent, u_coord, v_coord, poly_id, color):

        appended_ids = om.MIntArray()
        for i in xrange(position.length()):
            self.position.append(position[i])
            self.scale.append(scale[i])
            self.rotation.append(rotation[i])
            self.instance_id.append(instance_id[i])
            self.visibility.append(visibility[i])
            self.normal.append(normal[i])
            self.tangent.append(tangent[i])
            self.u_coord.append(u_coord[i])
            self.v_coord.append(v_coord[i])
            self.poly_id.append(poly_id[i])
            self.color.append(color[i])

            # append position to numpy array
            np_position = [[position[i].x, position[i].y, position[i].z]]
            self.np_position = np.append(self.np_position, np_position, axis=0)

            self.unique_id.append(self.position.length() - 1)
            appended_ids.append(self.position.length() - 1)

        return appended_ids


    def set_points(self, index, position=None, scale=None, rotation=None,
                   instance_id=None, visibility=None, normal=None,
                   tangent=None, u_coord=None, v_coord=None, poly_id=None,
                   color=None):
        """ set points identified by the given index for the given array(s)
        :param index list: list in indexes to set
        :param position MVectorArray: array of position data
        :param scalae MVectorArray:
        :param rotation MVectorArray:
        :param instance_id MIntArray
        :param visibility MIntArray
        :param normal MVectorArray
        :param tangent MVectorArray
        :param u_coord MDoubleArray
        :param v_coord MDoubleArray
        :param poly_id MIntArray
        :param color MVectorArray """

        # check input
        try:
            if position:
                assert len(index) == position.length()
                length = position.length()
            if scale:
                assert len(index) == scale.length()
                length = scale.length()
            if rotation:
                assert len(index) == rotation.length()
                length = rotation.length()
            if instance_id:
                assert len(index) == instance_id.length()
                length = instance_id.length()
            if visibility:
                assert len(index) == visibility.length()
                length = visibility.length()
            if normal:
                assert len(index) == normal.length()
                length = normal.length()
            if tangent:
                assert len(index) == tangent.length()
                length = tangent.length()
            if u_coord:
                assert len(index) == u_coord.length()
                length = u_coord.length()
            if v_coord:
                assert len(index) == v_coord.length()
                length = v_coord.length()
            if poly_id:
                assert len(index) == poly_id.length()
                length = poly_id.length()
            if color:
                assert len(index) == color.length()
                length = color.length()
        except AssertionError:
            raise RuntimeError('Could not set point: input array length does not match')

        # set points
        for i in xrange(length):
            if position:
                self.position.set(position[i], index[i])
                self.np_position.itemset((index[i], 0), position[i].x)
                self.np_position.itemset((index[i], 1), position[i].y)
                self.np_position.itemset((index[i], 2), position[i].z)
            if scale:
                self.scale.set(scale[i], index[i])
            if rotation:
                self.rotation.set(rotation[i], index[i])
            if instance_id:
                self.instance_id.set(instance_id[i], index[i])
            if visibility:
                self.visibility.set(visibility[i], index[i])
            if normal:
                self.normal.set(normal[i], index[i])
            if tangent:
                self.tangent.set(tangent[i], index[i])
            if u_coord:
                self.u_coord.set(u_coord[i], index[i])
            if v_coord:
                self.v_coord.set(v_coord[i], index[i])
            if poly_id:
                self.poly_id.set(poly_id[i], index[i])
            if color:
                assert len(index) == color.length()
                self.color.set(color[i], index[i])

    #  def delete_points(self, index):
    #      index = sorted(index, reverse=True)
    #      print index, len(index), self.position.length()
    #      for i in index:
    #          self.position.remove(i)
    #          self.np_position = np.delete(self.np_position, i, 0)
    #          self.scale.remove(i)
    #          self.rotation.remove(i)
    #          self.instance_id.remove(i)
    #          self.visibility.remove(i)
    #          self.normal.remove(i)
    #          self.tangent.remove(i)
    #          self.u_coord.remove(i)
    #          self.v_coord.remove(i)
    #          self.poly_id.remove(i)
    #          self.color.remove(i)
    #
    #      print self.position.length(), len(self.np_position)
    #      # TODO - a bit unfortunate but we have to rebuild our kd tree after
    #      # deleteing points / an alternative would be to hide object while
    #      # deleting and removing them at clean up
    #      self.build_kd_tree()

    def length(self):
        # TODO - do some checking if all the array are the same length?
        return self.position.length()

    def get_scale_average(self, index):
        """ get the average scale value for the given list of indexes
        @param index list: list of indexes
        @return x, y, z scale mean """

        scale_values = np.empty((0,3), float)
        for i in index:
            scale_values = np.append(scale_values, [[self.scale[i].x,
                                                     self.scale[i].y,
                                                     self.scale[i].z]],
                                     axis=0)

        scale_mean = np.mean(scale_values, axis=0)
        return scale_mean

    def get_rotation_average(self, index):
        """ get the average scale value for the given list of indexes
        @param index list: list of indexes
        @return x, y, z scale mean """

        rotation_value = np.empty((0,3), float)
        for i in index:
            rotation_value = np.append(rotation_value, [[self.rotation[i].x,
                                                         self.rotation[i].y,
                                                         self.rotation[i].z]],
                                     axis=0)

        rotation_value = np.mean(rotation_value, axis=0)
        return rotation_value

    def get_closest_points(self, position, radius, exclude=[]):
        """ get a list of all indexes within the given radius from the
        given position
        :param position: MPoint, List, tupe or np.array
        :param radius
        :param exclude: list of instance ids to exclude from nearest
                        neighbour search """

        if isinstance(position, om.MPoint):
            position = (position.x, position.y, position.z)
        neighbours = self.tree.query_ball_point(position, radius)

        if exclude:
            instance_ids = np.array([])
            for index in neighbours:
                instance_ids = np.append(instance_ids, self.instance_id[index])

            valid_index = np.array([])
            for index in exclude:
                valid_index = np.append(valid_index, np.where(instance_ids==index))

            neighbours = [neighbours[int(i)] for i in valid_index]
            return neighbours

        else:
            return list(neighbours)

    def clean_up(self):
        """ remove all points that a invisible after the delete brush
        has initially hidden them and is tearn down when the has been context left """

        invalid_ids = [i for i in xrange(self.visibility.length()) if self.visibility[i] == 0]
        invalid_ids = sorted(invalid_ids, reverse=True)

        for index in invalid_ids:
            self.position.remove(index)
            self.scale.remove(index)
            self.rotation.remove(index)
            self.instance_id.remove(index)
            self.visibility.remove(index)
            self.normal.remove(index)
            self.tangent.remove(index)
            self.u_coord.remove(index)
            self.v_coord.remove(index)
            self.poly_id.remove(index)
            self.color.remove(index)
            self.unique_id.remove(index)


    def __len__(self):
        return self.position.length()

    def __iter__(self):
        for i in xrange(self.position.length()):
            point = {'position': self.position[i],
                     'scale': self.scale[i],
                     'rotation': self.rotation[i],
                     'instance_id': self.instance_id[i],
                     'visibility': self.visibility[i],
                     'normal': self.normal[i],
                     'tangent': self.tangent[i],
                     'u': self.u_coord[i],
                     'v': self.v_coord[i],
                     'poly_id': self.poly_id[i],
                     'color': self.color[i],
                     'unique_id': self.unique_id[i]}

            yield point

    def __del__(self):
        print 'del ptc'

