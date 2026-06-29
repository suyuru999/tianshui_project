from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from .models import User, UserPermission
from .serializers import (
    UserSerializer, 
    UserCreateSerializer, 
    UserUpdateSerializer,
    AdminUserUpdateSerializer,
    UserPermissionSerializer,
    UserPermissionAssignmentSerializer,
    MODULE_PERMISSION_CHOICES,
)


def _is_admin_user(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == 'admin'))


class UserViewSet(viewsets.ModelViewSet):
    """用户视图集"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = []
    
    def get_queryset(self):
        if _is_admin_user(self.request.user):
            return User.objects.all().order_by('-date_joined')
        if self.request.user.is_authenticated:
            return User.objects.filter(id=self.request.user.id)
        return User.objects.none()

    def get_serializer_class(self):
        """根据操作类型选择序列化器"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            if _is_admin_user(self.request.user):
                return AdminUserUpdateSerializer
            return UserUpdateSerializer
        return UserSerializer
    
    def get_permissions(self):
        """设置权限"""
        if self.action in ['create', 'login']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        if not _is_admin_user(request.user):
            return Response({'error': '仅管理员可查看用户列表'}, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not _is_admin_user(request.user) and instance.id != request.user.id:
            return Response({'error': '仅可查看自己的用户信息'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not _is_admin_user(request.user) and instance.id != request.user.id:
            return Response({'error': '仅可修改自己的用户信息'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not _is_admin_user(request.user) and instance.id != request.user.id:
            return Response({'error': '仅可修改自己的用户信息'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not _is_admin_user(request.user):
            return Response({'error': '仅管理员可删除用户'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        if instance.id == request.user.id:
            return Response({'error': '不能删除当前登录管理员'}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """用户登录"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': '用户名和密码不能为空'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        if user is not None:
            if not user.is_active:
                return Response({'error': '用户已被禁用'}, status=status.HTTP_403_FORBIDDEN)
            login(request, user)
            serializer = UserSerializer(user)
            return Response({
                'message': '登录成功',
                'user': serializer.data
            })
        else:
            return Response(
                {'error': '用户名或密码错误'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """用户登出"""
        logout(request)
        return Response({'message': '登出成功'})
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """获取当前用户信息"""
        if not request.user.is_authenticated:
            return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        """更新当前用户信息"""
        if not request.user.is_authenticated:
            return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': '用户信息更新成功',
                'user': UserSerializer(request.user).data
            })
        else:
            return Response(
                {'error': '数据验证失败', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def me(self, request):
        """当前登录用户完整信息"""
        if not request.user.is_authenticated:
            return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=['get'])
    def permission_schema(self, request):
        """权限模块定义"""
        if not _is_admin_user(request.user):
            return Response({'error': '仅管理员可查看权限定义'}, status=status.HTTP_403_FORBIDDEN)
        return Response({
            'modules': MODULE_PERMISSION_CHOICES
        })

    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """获取指定用户权限"""
        target_user = self.get_object()
        if not _is_admin_user(request.user) and target_user.id != request.user.id:
            return Response({'error': '仅可查看自己的权限'}, status=status.HTTP_403_FORBIDDEN)
        items = UserPermission.objects.filter(user=target_user).order_by('module', 'permission')
        serializer = UserPermissionSerializer(items, many=True)
        return Response({
            'user_id': target_user.id,
            'permissions': serializer.data
        })

    @action(detail=True, methods=['put'])
    def assign_permissions(self, request, pk=None):
        """管理员分配用户权限"""
        if not _is_admin_user(request.user):
            return Response({'error': '仅管理员可分配权限'}, status=status.HTTP_403_FORBIDDEN)

        target_user = self.get_object()
        serializer = UserPermissionAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        permission_map = serializer.validated_data['permissions']

        UserPermission.objects.filter(user=target_user).delete()
        created_items = []
        for module, permissions_list in permission_map.items():
            for permission in permissions_list:
                created_items.append(
                    UserPermission(user=target_user, module=module, permission=permission, granted=True)
                )
        if created_items:
            UserPermission.objects.bulk_create(created_items)

        refreshed = UserPermission.objects.filter(user=target_user).order_by('module', 'permission')
        return Response({
            'message': '权限分配成功',
            'user': UserSerializer(target_user).data,
            'permissions': UserPermissionSerializer(refreshed, many=True).data
        })
